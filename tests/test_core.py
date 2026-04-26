from unittest.mock import MagicMock, patch

import pytest

from app.core import run
from app.db import VacancyStatus
from app.exceptions import VacancySkipWrongCountryError


def _make_settings():
    settings = MagicMock()
    settings.database_url = "sqlite:///:memory:"
    settings.hh_search_url = "http://hh.ru/search"
    settings.habr_search_url = None
    settings.response_limit_per_platform = None
    return settings


def _make_scraper(urls=None):
    scraper = MagicMock()
    scraper.get_job_urls.side_effect = urls if urls is not None else [
        ["http://hh.ru/vacancy/1", "http://hh.ru/vacancy/2"],
        [],
    ]
    scraper.has_next_page.return_value = False
    return scraper


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.exists.return_value = False
    return repo


def test_run_skips_already_processed_vacancy(mock_repo):
    settings = _make_settings()
    scraper = _make_scraper()
    mock_repo.exists.return_value = True

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch("app.core.VacancyProcessor"):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core.get_repository", return_value=mock_repo):
                        run()

    assert not mock_repo.save.called


def test_run_saves_responded_vacancies(mock_repo):
    settings = _make_settings()
    scraper = _make_scraper()

    vacancy_processor = MagicMock()
    vacancy_processor.is_correct_profession.return_value = True
    vacancy_processor.generate_response.return_value = "cover letter"

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch(
                "app.core.VacancyProcessor", return_value=vacancy_processor
            ):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core.get_repository", return_value=mock_repo):
                        run()

    assert mock_repo.save.call_count == 2
    for call in mock_repo.save.call_args_list:
        vacancy = call[0][0]
        assert vacancy.status == VacancyStatus.responded
        assert vacancy.cover_letter == "cover letter"
        assert vacancy.platform == "hh"


def test_run_saves_skipped_wrong_profession(mock_repo):
    settings = _make_settings()
    scraper = _make_scraper(urls=[["http://hh.ru/vacancy/1"], []])

    vacancy_processor = MagicMock()
    vacancy_processor.is_correct_profession.return_value = False

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch(
                "app.core.VacancyProcessor", return_value=vacancy_processor
            ):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core.get_repository", return_value=mock_repo):
                        run()

    assert mock_repo.save.call_count == 1
    vacancy = mock_repo.save.call_args[0][0]
    assert vacancy.status == VacancyStatus.skipped_wrong_profession
    assert vacancy.cover_letter is None
    assert vacancy.platform == "hh"


def test_run_saves_skipped_vacancy_on_vacancy_skip_error(mock_repo):
    settings = _make_settings()
    scraper = _make_scraper(urls=[["http://hh.ru/vacancy/1"], []])
    scraper.has_next_page.return_value = False
    scraper.response_to_vacancy.side_effect = VacancySkipWrongCountryError(
        "Вакансия в другой стране"
    )

    vacancy_processor = MagicMock()
    vacancy_processor.is_correct_profession.return_value = True
    vacancy_processor.generate_response.return_value = "response"

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch(
                "app.core.VacancyProcessor", return_value=vacancy_processor
            ):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core.get_repository", return_value=mock_repo):
                        run()

    assert mock_repo.save.call_count == 1
    vacancy = mock_repo.save.call_args[0][0]
    assert vacancy.status == VacancyStatus.skipped_other_country
    assert vacancy.cover_letter == "response"
    assert vacancy.url == "http://hh.ru/vacancy/1"


def test_run_closes_repo_on_keyboard_interrupt(mock_repo):
    settings = _make_settings()
    scraper = _make_scraper()
    scraper.get_job_urls.side_effect = KeyboardInterrupt()

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch("app.core.VacancyProcessor"):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core.get_repository", return_value=mock_repo):
                        run()

    assert mock_repo.close.called


def test_run_closes_repo_on_browser_closed_error(mock_repo):
    settings = _make_settings()
    scraper = _make_scraper(urls=[["http://hh.ru/vacancy/1"], []])
    scraper.open_vacancy_in_new_tab.side_effect = Exception(
        "Target page, context or browser has been closed"
    )

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch("app.core.VacancyProcessor"):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core.get_repository", return_value=mock_repo):
                        run()

    assert mock_repo.close.called
