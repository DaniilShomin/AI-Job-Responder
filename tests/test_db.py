import pytest

from app.db import (
    SQLiteRepository,
    PostgresRepository,
    get_repository,
    ProcessedVacancy,
    VacancyStatus,
    _coerce_datetime,
)


@pytest.fixture
def repo():
    r = SQLiteRepository("sqlite:///:memory:")
    r.init_schema()
    yield r
    r.close()


def test_init_schema_creates_table(repo):
    assert not repo.exists("http://example.com")


def test_exists_returns_false_for_new_url(repo):
    assert repo.exists("http://example.com") is False


def test_exists_returns_true_after_save(repo):
    vacancy = ProcessedVacancy(
        url="http://example.com",
        status=VacancyStatus.responded,
        platform="hh",
        title="Python Dev",
        cover_letter="Hello",
    )
    repo.save(vacancy)
    assert repo.exists("http://example.com") is True


def test_save_updates_existing_url(repo):
    url = "http://example.com"
    repo.save(
        ProcessedVacancy(
            url=url,
            status=VacancyStatus.responded,
            platform="hh",
            title="Python Dev",
            cover_letter="Hello",
        )
    )
    repo.save(
        ProcessedVacancy(
            url=url,
            status=VacancyStatus.skipped_wrong_profession,
            platform="hh",
            title="Java Dev",
            cover_letter=None,
        )
    )
    result = repo.get_by_url(url)
    assert result is not None
    assert result.status == VacancyStatus.skipped_wrong_profession
    assert result.title == "Java Dev"
    assert result.cover_letter is None
    assert result.created_at is not None
    assert result.updated_at is not None


def test_get_by_url_returns_none_for_missing(repo):
    assert repo.get_by_url("http://missing.com") is None


def test_get_by_url_returns_vacancy(repo):
    vacancy = ProcessedVacancy(
        url="http://example.com",
        status=VacancyStatus.skipped_questions,
        platform="habr",
        title="Senior Python",
        cover_letter="cover text",
    )
    repo.save(vacancy)
    result = repo.get_by_url("http://example.com")
    assert result is not None
    assert result.url == "http://example.com"
    assert result.status == VacancyStatus.skipped_questions
    assert result.platform == "habr"
    assert result.title == "Senior Python"
    assert result.cover_letter == "cover text"
    assert result.created_at is not None


def test_coerce_datetime_parses_iso_string():
    dt = _coerce_datetime("2024-01-15T10:30:00+00:00")
    assert dt.year == 2024
    assert dt.hour == 10


def test_coerce_datetime_returns_datetime_object():
    from datetime import datetime, timezone

    original = datetime.now(timezone.utc)
    dt = _coerce_datetime(original)
    assert dt is original


def test_get_repository_returns_sqlite():
    r = get_repository("sqlite:///:memory:")
    assert isinstance(r, SQLiteRepository)
    r.close()


def test_get_repository_raises_on_unknown_url():
    with pytest.raises(ValueError, match="Неподдерживаемый"):
        get_repository("mysql://localhost/db")
