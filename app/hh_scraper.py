import logging
from typing import Callable

from playwright.sync_api import Page

from app.base_scraper import BaseScraper
from app.exceptions import BrowserError, ScraperError, VacancySkipError

logger = logging.getLogger(__name__)


class HHVacancyScraper(BaseScraper):
    """Скрейпер вакансий с сайта hh.ru."""

    BASE_URL = "https://hh.ru"
    LOGIN_SELECTOR = 'a[data-qa="Login"]'
    SEARCH_BUTTON_SELECTOR = 'a[data-qa="applicant-index-search-all-results-button"]'
    JOB_TITLE_SELECTOR = 'a[data-qa="serp-item__title"]'
    VACANCY_DESC_SELECTOR = 'div[data-qa="vacancy-description"]'
    VACANCY_TITLE_SELECTOR = 'h1[data-qa="vacancy-title"]'
    FILL_SELECTOR = 'textarea[data-qa="vacancy-response-popup-form-letter-input"]'
    RESPONSE_BUTTON_SELECTOR = 'button[form="RESPONSE_MODAL_FORM_ID"]'
    NEXT_PAGE_SELECTOR = 'a[data-qa="pager-next"]'

    def __init__(self, page: Page) -> None:
        """Инициализирует скрейпер."""
        self.page = page

    def go_to_search(self) -> None:
        """Переходит на страницу поиска вакансий."""
        try:
            self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
            self.page.wait_for_load_state("domcontentloaded")
            logger.info("Переход на hh.ru выполнен успешно")
        except Exception as e:
            logger.error("Ошибка при переходе на hh.ru: %s", e)
            raise BrowserError(f"Не удалось открыть hh.ru: {e}") from e

    def login(self) -> None:
        try:
            element = self.page.query_selector(self.LOGIN_SELECTOR)
            if element:
                self.page.click("text=Войти")
                self.page.wait_for_load_state("domcontentloaded")
                self.page.click("text=Войти")
                self.page.wait_for_selector('text="Резюме и профиль"')
                logger.info("Вход выполнен успешно")
            else:
                logger.info("Элемент входа не найден, возможно уже выполнен вход")
        except Exception as e:
            logger.error("Ошибка при входе на hh.ru: %s", e)
            raise BrowserError(f"Не удалось войти на hh.ru: {e}") from e

    def navigate_to_job_search(self, search_url: str | None = None) -> None:
        try:
            if search_url:
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            else:
                # Нажимаем кнопку поиска
                self.page.locator(
                    self.SEARCH_BUTTON_SELECTOR
                ).scroll_into_view_if_needed()
                self.page.click(self.SEARCH_BUTTON_SELECTOR)

            self.page.wait_for_load_state("domcontentloaded")
            logger.info("Переход на страницу поиска выполнен успешно")
        except Exception as e:
            logger.error("Ошибка при переходе на страницу поиска: %s", e)
            raise BrowserError(f"Не удалось открыть страницу поиска: {e}") from e

    def get_job_urls(self) -> list[str]:
        """Получает URL всех вакансий на текущей странице."""
        try:
            elements = self.page.locator(self.JOB_TITLE_SELECTOR)
            count = elements.count()

            urls = []
            for i in range(count):
                href = elements.nth(i).get_attribute("href")
                if href:
                    urls.append(href.split("?")[0])

            return urls
        except Exception as e:
            logger.error("Ошибка при получении URL вакансий: %s", e)
            return []

    def get_vacancy_details(self, page: Page) -> dict[str, str] | None:
        """Получает название и описание вакансии."""
        try:
            title_elem = page.locator(self.VACANCY_TITLE_SELECTOR)
            desc_elem = page.locator(self.VACANCY_DESC_SELECTOR)

            if desc_elem.count() == 0:
                return None

            title = title_elem.inner_text() if title_elem.count() > 0 else "N/A"
            description = desc_elem.inner_text()

            return {
                "title": title,
                "description": description,
            }
        except Exception as e:
            logger.error("Ошибка при получении деталей вакансии: %s", e)
            return None

    def open_vacancy_in_new_tab(self, vacancy_url: str) -> Page:
        """Открывает вакансию в новой вкладке"""
        with self.page.expect_event("popup") as popup_info:
            self.page.locator(f"a[href*='{vacancy_url}']").click()
        new_tab: Page = popup_info.value
        new_tab.wait_for_load_state("domcontentloaded")
        new_tab.bring_to_front()
        return new_tab

    def close_vacancy_tab(self, page: Page) -> None:
        """Закрывает вкладку с вакансией"""
        try:
            page.close()
        except Exception as e:
            error_msg = f"Ошибка при закрытии вкладки вакансии: {e}"
            logger.error(error_msg)
            raise ScraperError(error_msg) from e

    def response_to_vacancy(
        self, page: Page, response_text: str, random_sleep: Callable
    ) -> None:
        """Основной метод для отклика на вакансию с обработкой различных случаев."""
        try:
            if not self._is_respond_button_present(page):
                logger.warning("Кнопка 'Откликнуться' не найдена, пропуск вакансии.")
                raise VacancySkipError("Кнопка 'Откликнуться' не найдена")

            page.click("text=Откликнуться")
            random_sleep(2, 4)

            # Проверяем ограничения
            if self._is_vacancy_in_another_country(page):
                logger.warning("Вакансия в другой стране, пропуск.")
                raise VacancySkipError("Вакансия в другой стране")
            if self._requires_additional_questions(page):
                logger.warning("Требуются дополнительные вопросы, пропуск.")
                raise VacancySkipError("Требуются дополнительные вопросы работодателя")
        except VacancySkipError:
            raise
        except ScraperError:
            raise
        except Exception as e:
            raise ScraperError(f"Ошибка при подготовке отклика: {e}") from e
        try:
            # Заполняем сопроводительное письмо, если требуется
            self._fill_cover_letter(page, response_text, random_sleep)
        except ScraperError:
            raise
        except Exception as e:
            raise ScraperError(f"Ошибка при заполнении сопроводительного письма: {e}") from e
        try:
            # Отправка отклика
            self._submit_response(page)
            logger.info("Отклик на вакансию успешно отправлен.")

        except Exception as e:
            error_msg = f"Ошибка при отклике на вакансию: {e}"
            logger.error(error_msg)
            raise ScraperError(error_msg) from e

    def _is_respond_button_present(self, page: Page) -> bool:
        """Проверяет наличие кнопки 'Откликнуться'."""
        return page.locator("text=Откликнуться").count() > 0

    def _is_vacancy_in_another_country(self, page: Page) -> bool:
        """Проверяет, находится ли вакансия в другой стране."""
        locator = page.locator('text="Вы откликаетесь на вакансию в другой стране"')
        return locator.count() > 0

    def _requires_additional_questions(self, page: Page) -> bool:
        """Проверяет, требует ли вакансия ответов на вопросы."""
        locator = page.locator(
            'text="Для отклика необходимо ответить на несколько вопросов работодателя"'
        )
        return locator.count() > 0

    def _has_cover_letter_requirement(self, page: Page) -> bool:
        """Проверяет, нужно ли добавить сопроводительное письмо."""
        locator = page.locator(
            'text="Сопроводительное письмо обязательное для этой вакансии"'
        )
        return locator.count() > 0

    def _fill_cover_letter(
        self, page: Page, response_text: str, random_sleep: Callable
    ) -> None:
        """Добавляет и заполняет сопроводительное письмо."""
        try:
            if not self._has_cover_letter_requirement(page):
                page.click("text=Добавить сопроводительное")
            random_sleep(1, 2)

            textarea = page.wait_for_selector(
                self.FILL_SELECTOR,
                timeout=10000,
            )
            if textarea:
                textarea.fill(response_text)
            random_sleep(2, 4)
        except Exception as e:
            logger.warning("Не удалось заполнить сопроводительное письмо: %s", e)
            raise

    def _submit_response(self, page: Page) -> None:
        """Нажимает кнопку отправки отклика."""
        try:
            page.click(self.RESPONSE_BUTTON_SELECTOR)
        except Exception as e:
            logger.error("Не удалось отправить отклик: %s", e)
            raise

    def has_next_page(self) -> bool:
        """Проверяет наличие следующей страницы результатов."""
        return self.page.locator(self.NEXT_PAGE_SELECTOR).count() > 0

    def go_to_next_page(self) -> None:
        """Переходит на следующую страницу результатов."""
        try:
            self.page.click(self.NEXT_PAGE_SELECTOR)
            self.page.wait_for_load_state("domcontentloaded")
            logger.info("Переход на следующую страницу выполнен")
        except Exception as e:
            logger.error("Ошибка при переходе на следующую страницу: %s", e)
            raise BrowserError(f"Не удалось перейти на следующую страницу: {e}") from e
