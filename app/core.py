import logging

from app.ai import AIClient
from app.browser import BrowserContext
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
        logger.error("Ошибка инициализации процессора вакансий: %s", e)
        return

    with BrowserContext(settings=settings) as scraper:
        try:
            scraper.go_to_hh()
            scraper.login()
            random_sleep()

            hh_search_url = settings.get("hh_search_url")
            scraper.navigate_to_job_search(search_url=hh_search_url)
            random_sleep()
        except BrowserError as e:
            logger.error("Ошибка браузера: %s", e)
            return
        except Exception as e:
            logger.error("Неизвестная ошибка при инициализации скрейпера: %s", e)
            return

        filename = settings["data_file"]
        try:
            vacancy_list = load_json(filename)
        except LoadingError as e:
            logger.warning("Ошибка загрузки файла данных: %s", e)
            vacancy_list = []

        logger.info("Загружено элементов: %s", len(vacancy_list))

        urls = scraper.get_job_urls()
        logger.info("Найдено %s вакансий на странице", len(urls))
        for url in urls:
            try:
                if url in vacancy_list:
                    logger.info("Вакансия уже обработана: %s", url)
                    continue
                logger.info("Открытие вакансии: %s", url)
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
                    vacancy_list.append(url)
                    random_sleep(2, 4)
                    continue
                try:
                    response = vacancy_processor.generate_response(
                        vacancy_title=details["title"],
                        vacancy_description=details["description"],
                    )
                except TimeoutError as e:
                    logger.warning("Превышено время ожидания от AI API: %s", e)
                    raise
                except OpenAIError as e:
                    logger.warning("Ошибка AI API: %s", e)
                    raise
                try:
                    scraper.response_to_vacancy(new_tab, response, random_sleep)
                except ScraperError as e:
                    logger.warning("Ошибка при отклике на вакансию: %s", e)
                    raise
                random_sleep(2, 4)
                try:
                    scraper.close_vacancy_tab(new_tab)
                except ScraperError as e:
                    logger.warning("Ошибка при закрытии вкладки вакансии: %s", e)
                    raise
                vacancy_list.append(url)
                random_sleep(2, 4)
            except Exception as e:
                logger.warning("Ошибка при обработке вакансий: %s", e)
        try:
            save_json(filename, vacancy_list)
        except SavingError as e:
            logger.warning("Ошибка сохранения файла данных: %s", e)
        logger.info("Сохранено элементов: %s", len(vacancy_list))
