import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core import _safe_save, run
from app.exceptions import SavingError, VacancySkipError


def test_safe_save_success(tmp_path: Path, caplog):
    caplog.set_level(logging.INFO)
    filepath = tmp_path / "data.json"
    data = ["url1", "url2"]
    _safe_save(str(filepath), data)
    assert json.loads(filepath.read_text(encoding="utf-8")) == data
    assert "Сохранено элементов: 2" in caplog.text


def test_safe_save_error_logs_warning(caplog):
    caplog.set_level(logging.WARNING)
    with patch("app.core.save_json_atomic", side_effect=SavingError("disk full")):
        _safe_save("/some/path.json", ["url1"])
    assert "Ошибка сохранения файла данных: disk full" in caplog.text


def test_run_saves_incrementally(tmp_path: Path):
    settings = MagicMock()
    settings.data_file = str(tmp_path / "vacancies.json")
    settings.hh_search_url = "http://hh.ru/search"
    settings.habr_search_url = None

    scraper = MagicMock()
    scraper.get_job_urls.return_value = [
        "http://hh.ru/vacancy/1",
        "http://hh.ru/vacancy/2",
    ]
    scraper.has_next_page.return_value = False

    vacancy_processor = MagicMock()
    vacancy_processor.is_correct_profession.return_value = True
    vacancy_processor.generate_response.return_value = "response"

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch("app.core.VacancyProcessor", return_value=vacancy_processor):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core._safe_save") as mock_save:
                        run()

    # _safe_save должен вызываться после каждой обработанной вакансии
    # (2 вакансии) + финальное сохранение в finally
    assert mock_save.call_count >= 2


def test_run_saves_on_keyboard_interrupt(tmp_path: Path):
    settings = MagicMock()
    settings.data_file = str(tmp_path / "vacancies.json")
    settings.hh_search_url = "http://hh.ru/search"
    settings.habr_search_url = None

    scraper = MagicMock()
    scraper.get_job_urls.side_effect = KeyboardInterrupt()

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch("app.core.VacancyProcessor"):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core._safe_save") as mock_save:
                        run()

    assert mock_save.called


def test_run_saves_on_browser_closed_error(tmp_path: Path):
    settings = MagicMock()
    settings.data_file = str(tmp_path / "vacancies.json")
    settings.hh_search_url = "http://hh.ru/search"
    settings.habr_search_url = None

    scraper = MagicMock()
    scraper.get_job_urls.return_value = ["http://hh.ru/vacancy/1"]
    scraper.open_vacancy_in_new_tab.side_effect = Exception(
        "Target page, context or browser has been closed"
    )

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch("app.core.VacancyProcessor"):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core._safe_save") as mock_save:
                        run()

    # _safe_save должен быть вызван хотя бы в finally
    assert mock_save.called


def test_run_saves_skipped_vacancy_on_vacancy_skip_error(tmp_path: Path):
    settings = MagicMock()
    settings.data_file = str(tmp_path / "vacancies.json")
    settings.hh_search_url = "http://hh.ru/search"
    settings.habr_search_url = None

    scraper = MagicMock()
    scraper.get_job_urls.return_value = ["http://hh.ru/vacancy/1"]
    scraper.has_next_page.return_value = False
    scraper.response_to_vacancy.side_effect = VacancySkipError(
        "Вакансия в другой стране"
    )

    vacancy_processor = MagicMock()
    vacancy_processor.is_correct_profession.return_value = True
    vacancy_processor.generate_response.return_value = "response"

    with patch("app.core.get_settings", return_value=settings):
        with patch("app.core.AIClient"):
            with patch("app.core.VacancyProcessor", return_value=vacancy_processor):
                with patch("app.core.BrowserContext") as mock_browser:
                    mock_browser.return_value.__enter__ = lambda self: scraper
                    mock_browser.return_value.__exit__ = lambda self, *args: None
                    with patch("app.core._safe_save") as mock_save:
                        run()

    # URL должен быть сохранён в vacancy_list, несмотря на VacancySkipError
    saved_lists = [call[0][1] for call in mock_save.call_args_list]
    assert any("http://hh.ru/vacancy/1" in lst for lst in saved_lists)
