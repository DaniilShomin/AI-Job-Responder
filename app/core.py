import logging

from app.ai import AIClient
from app.browser import BrowserContext
from app.vacancy_processor import VacancyProcessor
from app.config import get_settings
from app.db import get_repository, ProcessedVacancy, VacancyStatus
from app.utils import random_sleep
from app.exceptions import (
    BrowserError,
    LoadingError,
    ScraperError,
    VacancySkipError,
    VacancySkipNoButtonError,
    VacancySkipQuestionsError,
    VacancySkipWrongCountryError,
)
from app.base_scraper import BaseScraper
from app.habr_scraper import HabrVacancyScraper
from app.hh_scraper import HHVacancyScraper


logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """Настраивает логирование приложения."""
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def run() -> None:
    setup_logging("INFO")
    settings = get_settings()

    ai_client = AIClient(
        api_key=settings.api_key,
        model=settings.model,
        base_url=settings.api_base_url,
        timeout=settings.timeout,
    )
    try:
        vacancy_processor = VacancyProcessor(
            ai_client=ai_client,
            resume_path=settings.resume_file,
            prompt_path=settings.prompt_file,
            correct_professions=settings.correct_professions,
            grade_levels=settings.grade_levels,
        )
    except LoadingError as e:
        logger.error("Ошибка инициализации процессора вакансий: %s", e)
        return

    repo = get_repository(settings.database_url)
    repo.init_schema()

    scrapers: dict[type[BaseScraper], str | None] = {
        HHVacancyScraper: settings.hh_search_url,
        HabrVacancyScraper: settings.habr_search_url,
    }

    try:
        for scraper_class, search_url in scrapers.items():
            platform = "hh" if scraper_class is HHVacancyScraper else "habr"
            try:
                with BrowserContext(settings=settings, scraper=scraper_class) as scraper:
                    try:
                        scraper.go_to_search()
                        scraper.login(timeout=settings.login_timeout)
                        random_sleep()

                        scraper.navigate_to_job_search(search_url=search_url)
                        random_sleep()
                    except BrowserError as e:
                        logger.error("Ошибка браузера: %s", e)
                        return
                    except Exception as e:
                        logger.error(
                            "Неизвестная ошибка при инициализации скрейпера: %s", e
                        )
                        return

                    browser_closed = False
                    limit_reached = False
                    response_count = 0
                    try:
                        while True:
                            urls = scraper.get_job_urls()
                            urls = [
                                url for url in urls if url and "adsrv.hh.ru" not in url
                            ]
                            logger.info("Найдено %s вакансий на странице", len(urls))
                            for url in urls:
                                try:
                                    if repo.exists(url):
                                        logger.info(
                                            "Вакансия уже обработана: %s", url
                                        )
                                        continue
                                    logger.info("Открытие вакансии: %s", url)
                                    new_tab = scraper.open_vacancy_in_new_tab(url)
                                    random_sleep()

                                    details = scraper.get_vacancy_details(new_tab)
                                    if details is None:
                                        logger.warning(
                                            "Не удалось получить детали вакансии, пропускаем."
                                        )
                                        scraper.close_vacancy_tab(new_tab)
                                        random_sleep(2, 4)
                                        continue

                                    if not vacancy_processor.is_correct_profession(
                                        details["description"]
                                    ):
                                        logger.info(
                                            "Профессия не подходит, пропускаем вакансию."
                                        )
                                        scraper.close_vacancy_tab(new_tab)
                                        repo.save(
                                            ProcessedVacancy(
                                                url=url,
                                                status=VacancyStatus.skipped_wrong_profession,
                                                platform=platform,
                                                title=details.get("title"),
                                                cover_letter=None,
                                            )
                                        )
                                        random_sleep(2, 4)
                                        continue
                                    response = vacancy_processor.generate_response(
                                        vacancy_title=details["title"],
                                        vacancy_description=details["description"],
                                    )
                                    try:
                                        scraper.response_to_vacancy(
                                            new_tab, response, random_sleep
                                        )
                                    except VacancySkipError as e:
                                        logger.warning("Вакансия пропущена: %s", e)
                                        try:
                                            scraper.close_vacancy_tab(new_tab)
                                        except ScraperError:
                                            pass

                                        if isinstance(e, VacancySkipWrongCountryError):
                                            status = VacancyStatus.skipped_other_country
                                        elif isinstance(e, VacancySkipQuestionsError):
                                            status = VacancyStatus.skipped_questions
                                        elif isinstance(e, VacancySkipNoButtonError):
                                            status = VacancyStatus.skipped_no_button
                                        else:
                                            status = VacancyStatus.skipped_no_button

                                        repo.save(
                                            ProcessedVacancy(
                                                url=url,
                                                status=status,
                                                platform=platform,
                                                title=details.get("title"),
                                                cover_letter=response,
                                            )
                                        )
                                        continue
                                    except ScraperError as e:
                                        logger.warning(
                                            "Ошибка при отклике на вакансию: %s", e
                                        )
                                        scraper.close_vacancy_tab(new_tab)
                                        raise
                                    random_sleep(2, 4)
                                    try:
                                        scraper.close_vacancy_tab(new_tab)
                                    except ScraperError as e:
                                        logger.warning(
                                            "Ошибка при закрытии вкладки вакансии: %s",
                                            e,
                                        )
                                        raise
                                    repo.save(
                                        ProcessedVacancy(
                                            url=url,
                                            status=VacancyStatus.responded,
                                            platform=platform,
                                            title=details.get("title"),
                                            cover_letter=response,
                                        )
                                    )
                                    response_count += 1
                                    logger.info(
                                        "Откликов отправлено на %s: %s",
                                        scraper_class.__name__,
                                        response_count,
                                    )
                                    if (
                                        settings.response_limit_per_platform is not None
                                        and response_count
                                        >= settings.response_limit_per_platform
                                    ):
                                        logger.info(
                                            "Достигнут лимит откликов (%s) для платформы %s",
                                            settings.response_limit_per_platform,
                                            scraper_class.__name__,
                                        )
                                        limit_reached = True
                                        break
                                    random_sleep(2, 4)
                                except Exception as e:
                                    logger.warning(
                                        "Ошибка при обработке вакансий: %s", e
                                    )
                                    if "browser has been closed" in str(e).lower():
                                        logger.error(
                                            "Браузер был закрыт. Завершение обработки."
                                        )
                                        browser_closed = True
                                        break

                            if browser_closed or limit_reached:
                                break

                            try:
                                if not scraper.has_next_page():
                                    break
                                scraper.go_to_next_page()
                                random_sleep()
                            except Exception as e:
                                logger.error(
                                    "Ошибка при навигации по страницам: %s", e
                                )
                                break
                    except KeyboardInterrupt:
                        logger.info("Работа прервана пользователем (Ctrl+C)")
            except KeyboardInterrupt:
                logger.info("Работа прервана пользователем (Ctrl+C)")
                break
    finally:
        repo.close()
