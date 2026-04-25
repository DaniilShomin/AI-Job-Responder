import logging
from typing import Callable

from playwright.sync_api import Page

from app.base_scraper import BaseScraper
from app.exceptions import BrowserError, ScraperError, VacancySkipError

logger = logging.getLogger(__name__)


class HabrVacancyScraper(BaseScraper):
    """Скрейпер вакансий с сайта career.habr.com."""

    BASE_URL = "https://career.habr.com"
    LOGIN_SELECTOR = 'button[data-header-dropdown-toggle="user-auth-menu-desktop"]'
    SEARCH_BUTTON_SELECTOR = 'a[href="https://career.habr.com/vacancies"]'
    SEARCH_BUTTON_SELECTOR_SUITABLE = (
        'a[href="https://career.habr.com/vacancies?type=suitable"]'
    )
    JOB_TITLE_SELECTOR = 'a[class="vacancy-card__title-link"]'
    VACANCY_DESC_SELECTOR = 'div[class="vacancy-description__text"]'
    VACANCY_TITLE_SELECTOR = 'h1[class="page-title__title"]'
    FILL_SELECTOR = 'textarea[class="basic-textarea__textarea"]'
    RESPONSE_BUTTON_SELECTOR = 'text="Дополнить отклик"'

    def __init__(self, page: Page) -> None:
        """Инициализирует скрейпер."""
        self.page = page
        self._block_third_party_requests()

    def _block_third_party_requests(self) -> None:
        def handler(route):
            url = route.request.url

            # Блокируем facebook pixel
            if "facebook.com/tr" in url:
                route.abort()
                return

            route.continue_()

        self.page.route("**/*", handler)

    def go_to_search(self) -> None:
        """Переходит на страницу поиска вакансий."""
        try:
            self.page.goto(self.BASE_URL, wait_until="domcontentloaded")
            logger.info("Переход на career.habr.com выполнен успешно")
        except Exception as e:
            logger.error("Ошибка при переходе на career.habr.com: %s", e)
            raise BrowserError(f"Не удалось открыть career.habr.com: {e}") from e

    def login(self) -> None:
        try:
            element = self.page.query_selector(self.LOGIN_SELECTOR)
            if element:
                logger.info("Ожидание входа")
                self.page.wait_for_selector('button[title="Личное меню"]')
                logger.info("Вход выполнен успешно")
            else:
                logger.info("Элемент входа не найден, возможно уже выполнен вход")
        except Exception as e:
            logger.error("Ошибка при входе на career.habr.com: %s", e)
            raise BrowserError(f"Не удалось войти на career.habr.com: {e}") from e

    def navigate_to_job_search(self, search_url: str | None = None) -> None:
        try:
            url = search_url or f"{self.BASE_URL}/vacancies?type=suitable"

            self.page.goto(
                url,
                wait_until="domcontentloaded",
            )

            # ждём появление карточек вакансий
            self.page.wait_for_selector(self.JOB_TITLE_SELECTOR)

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
                    urls.append(f"https://career.habr.com{href}")

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
        new_tab = self.page.context.new_page()
        new_tab.goto(vacancy_url, wait_until="domcontentloaded")
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
            random_sleep()
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
        try:
            textarea = page.locator(self.FILL_SELECTOR).first

            # Ждём только появления в DOM (НЕ visible)
            textarea.wait_for(state="attached", timeout=7000)

            # Заполняем (fill сам дождётся, пока элемент станет interactable)
            textarea.fill(response_text)
            random_sleep()

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
        # TODO: реализовать пагинацию для Habr Career
        return False

    def go_to_next_page(self) -> None:
        """Переходит на следующую страницу результатов."""
        pass
