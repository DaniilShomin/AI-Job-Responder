import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

from app.exceptions import ValidationError

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Настройки приложения"""

    api_key: str
    api_base_url: str
    model: str
    hh_search_url: str | None
    habr_search_url: str | None
    headless: bool
    timeout: int
    login_timeout: int
    database_url: str
    resume_file: str
    prompt_file: str
    response_limit_per_platform: int | None
    correct_professions: list[str] | None
    grade_levels: list[str] | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Получение настроек из переменных окружения"""
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValidationError("API_KEY не установлен в переменных окружения")

    response_limit_raw = os.getenv("RESPONSE_LIMIT_PER_PLATFORM")
    if response_limit_raw == "":
        response_limit_per_platform = None
    elif response_limit_raw is None:
        response_limit_per_platform = 10
    else:
        response_limit_per_platform = int(response_limit_raw)

    correct_professions_raw = os.getenv("CORRECT_PROFESSIONS")
    if correct_professions_raw:
        correct_professions = [p.strip().lower() for p in correct_professions_raw.split(",")]
    else:
        correct_professions = None

    grade_levels_raw = os.getenv("GRADE_LEVELS")
    if grade_levels_raw:
        grade_levels = [g.strip().lower() for g in grade_levels_raw.split(",")]
    else:
        grade_levels = None

    return Settings(
        api_key=api_key,
        api_base_url=os.getenv("API_BASE_URL", "https://routerai.ru/api/v1"),
        model=os.getenv("MODEL", "stepfun/step-3.5-flash:free"),
        hh_search_url=os.getenv("HH_SEARCH_URL"),
        habr_search_url=os.getenv("HABR_SEARCH_URL"),
        headless=os.getenv("HEADLESS", "true").lower() == "true",
        timeout=int(os.getenv("TIMEOUT", "10")),
        login_timeout=int(os.getenv("LOGIN_TIMEOUT", "60000")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///vacancies.db"),
        resume_file=os.getenv("RESUME_FILE", "resume.txt"),
        prompt_file=os.getenv("PROMPT_FILE", "prompt.txt"),
        response_limit_per_platform=response_limit_per_platform,
        correct_professions=correct_professions,
        grade_levels=grade_levels,
    )
