import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment, misc]


class VacancyStatus(StrEnum):
    responded = "responded"
    skipped_wrong_profession = "skipped_wrong_profession"
    skipped_other_country = "skipped_other_country"
    skipped_questions = "skipped_questions"
    skipped_no_button = "skipped_no_button"


@dataclass
class ProcessedVacancy:
    url: str
    status: VacancyStatus
    platform: str
    title: str | None
    cover_letter: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VacancyRepository(ABC):
    @abstractmethod
    def init_schema(self) -> None:
        """Создаёт таблицы, если они не существуют."""

    @abstractmethod
    def exists(self, url: str) -> bool:
        """Проверяет, есть ли вакансия в базе."""

    @abstractmethod
    def save(self, vacancy: ProcessedVacancy) -> None:
        """Сохраняет или обновляет вакансию."""

    @abstractmethod
    def get_by_url(self, url: str) -> ProcessedVacancy | None:
        """Возвращает вакансию по URL или None."""

    @abstractmethod
    def close(self) -> None:
        """Закрывает соединение с БД."""


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Unexpected datetime type: {type(value)}")


class SQLiteRepository(VacancyRepository):
    def __init__(self, database_url: str) -> None:
        path = database_url.replace("sqlite://", "")
        if path.startswith("/"):
            path = path[1:]
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_vacancies (
                url TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                platform TEXT NOT NULL,
                title TEXT,
                cover_letter TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def exists(self, url: str) -> bool:
        cursor = self._conn.execute(
            "SELECT 1 FROM processed_vacancies WHERE url = ?",
            (url,),
        )
        return cursor.fetchone() is not None

    def save(self, vacancy: ProcessedVacancy) -> None:
        now = datetime.now(timezone.utc)
        self._conn.execute(
            """
            INSERT INTO processed_vacancies
                (url, status, platform, title, cover_letter, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                status = excluded.status,
                platform = excluded.platform,
                title = excluded.title,
                cover_letter = excluded.cover_letter,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                vacancy.url,
                vacancy.status.value,
                vacancy.platform,
                vacancy.title,
                vacancy.cover_letter,
                now.isoformat(),
            ),
        )
        self._conn.commit()

    def get_by_url(self, url: str) -> ProcessedVacancy | None:
        cursor = self._conn.execute(
            "SELECT * FROM processed_vacancies WHERE url = ?",
            (url,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_vacancy(row)

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_vacancy(row: sqlite3.Row) -> ProcessedVacancy:
        return ProcessedVacancy(
            url=row["url"],
            status=VacancyStatus(row["status"]),
            platform=row["platform"],
            title=row["title"],
            cover_letter=row["cover_letter"],
            created_at=_coerce_datetime(row["created_at"]),
            updated_at=_coerce_datetime(row["updated_at"]),
        )


class PostgresRepository(VacancyRepository):
    def __init__(self, database_url: str) -> None:
        if psycopg is None:
            raise RuntimeError(
                "psycopg не установлен. Установите зависимость psycopg[binary]"
            )
        self._conn = psycopg.connect(database_url, row_factory=dict_row)

    def init_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_vacancies (
                    url VARCHAR PRIMARY KEY,
                    status VARCHAR NOT NULL,
                    platform VARCHAR NOT NULL,
                    title TEXT,
                    cover_letter TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        self._conn.commit()

    def exists(self, url: str) -> bool:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM processed_vacancies WHERE url = %s",
                (url,),
            )
            return cur.fetchone() is not None

    def save(self, vacancy: ProcessedVacancy) -> None:
        now = datetime.now(timezone.utc)
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO processed_vacancies
                    (url, status, platform, title, cover_letter, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(url) DO UPDATE SET
                    status = excluded.status,
                    platform = excluded.platform,
                    title = excluded.title,
                    cover_letter = excluded.cover_letter,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    vacancy.url,
                    vacancy.status.value,
                    vacancy.platform,
                    vacancy.title,
                    vacancy.cover_letter,
                    now,
                ),
            )
        self._conn.commit()

    def get_by_url(self, url: str) -> ProcessedVacancy | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM processed_vacancies WHERE url = %s",
                (url,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_vacancy(row)

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_vacancy(row: dict[str, Any]) -> ProcessedVacancy:
        return ProcessedVacancy(
            url=row["url"],
            status=VacancyStatus(row["status"]),
            platform=row["platform"],
            title=row["title"],
            cover_letter=row["cover_letter"],
            created_at=_coerce_datetime(row["created_at"]),
            updated_at=_coerce_datetime(row["updated_at"]),
        )


def get_repository(database_url: str) -> VacancyRepository:
    if database_url.startswith("sqlite"):
        return SQLiteRepository(database_url)
    if database_url.startswith("postgresql"):
        return PostgresRepository(database_url)
    raise ValueError(f"Неподдерживаемый DATABASE_URL: {database_url}")
