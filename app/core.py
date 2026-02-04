import logging
from playwright.sync_api import sync_playwright

from app.ai import AIClient
from app.hh_scraper import HHVacancyScraper
from app.vacancy_processor import VacancyProcessor
from app.config import settings
from app.utils import random_sleep, load_json, save_json
from app.exceptions import (
    OpenAIError,
    BrowserError,
    LoadingError,
    SavingError,
    ScraperError,
)


logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """Настраивает логирование приложения."""
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def run() -> None:
    setup_logging("INFO")
    ai_client = AIClient(
        api_key=settings["api_key"],
        model=settings["model"],
        timeout=settings.get("timeout", 10),
    )
    try:
        vacancy_processor = VacancyProcessor(
            ai_client=ai_client,
            resume_path=settings["resume_file"],
            prompt_path=settings["prompt_file"],
        )
    except LoadingError as e:
        logger.error(f"Ошибка инициализации процессора вакансий: {e}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            context = browser.new_context(storage_state="auth_state.json")
        except Exception:
            context = browser.new_context()
        scraper = HHVacancyScraper(page=context.new_page())
        try:
            scraper.go_to_hh()
            scraper.login()
            random_sleep()

            hh_search_url = settings.get("hh_search_url")
            scraper.navigate_to_job_search(search_url=hh_search_url)
            random_sleep()
        except BrowserError as e:
            logger.error(f"Ошибка браузера: {e}")
            browser.close()
            return
        except Exception as e:
            logger.error(f"Неизвестная ошибка при инициализации скрейпера: {e}")
            browser.close()
            return

        filename = settings["data_file"]
        try:
            vacancy_list = load_json(filename)
        except LoadingError as e:
            logger.warning(f"Ошибка загрузки файла данных: {e}")
            vacancy_list = []

        logger.info(f"Загружено элементов: {len(vacancy_list)}")

        urls = scraper.get_job_urls()
        try:
            for url in urls:
                if url in vacancy_list:
                    logger.info(f"Вакансия уже обработана: {url}")
                    continue
                logger.info(f"Открытие вакансии: {url}")
                new_tab = scraper.open_vacancy_in_new_tab(url)
                random_sleep()

                details = scraper.get_vacancy_details(new_tab)
                if details is None:
                    logger.warning("Не удалось получить детали вакансии, пропускаем.")
                    scraper.close_vacancy_tab(new_tab)
                    random_sleep(2, 4)
                    continue

                if not vacancy_processor.is_correct_profession(details["description"]):
                    logger.info("Профессия не подходит, пропускаем вакансию.")
                    scraper.close_vacancy_tab(new_tab)
                    random_sleep(2, 4)
                    continue
                try:
                    response = vacancy_processor.generate_response(
                        vacancy_title=details["title"],
                        vacancy_description=details["description"],
                    )
                except TimeoutError as e:
                    logger.warning(f"Превышено время ожидания от AI API: {e}")
                    raise
                except OpenAIError as e:
                    logger.warning(f"Ошибка AI API: {e}")
                    raise
                try:
                    scraper.response_to_vacancy(new_tab, response, random_sleep)
                except ScraperError as e:
                    logger.warning(f"Ошибка при отклике на вакансию: {e}")
                    raise
                random_sleep(2, 4)
                try:
                    scraper.close_vacancy_tab(new_tab)
                except ScraperError as e:
                    logger.warning(f"Ошибка при закрытии вкладки вакансии: {e}")
                    raise
                vacancy_list.append(url)
                random_sleep(2, 4)
        except Exception as e:
            logger.warning(f"Ошибка при обработке вакансий: {e}")
        try:
            save_json(filename, vacancy_list)
        except SavingError as e:
            logger.warning(f"Ошибка сохранения файла данных: {e}")
        logger.info(f"Сохранено элементов: {len(vacancy_list)}")
        context.storage_state(path="auth_state.json")
        browser.close()
