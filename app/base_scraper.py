from abc import ABC, abstractmethod
from typing import Callable

from playwright.sync_api import Page


class BaseScraper(ABC):
    def __init__(self, page: Page) -> None:
        pass

    @abstractmethod
    def go_to_search(self) -> None:
        pass

    @abstractmethod
    def login(self) -> None:
        pass

    @abstractmethod
    def navigate_to_job_search(self, search_url: str | None = None) -> None:
        pass

    @abstractmethod
    def get_job_urls(self) -> list[str]:
        pass

    @abstractmethod
    def get_vacancy_details(self, page: Page) -> dict[str, str] | None:
        pass

    @abstractmethod
    def open_vacancy_in_new_tab(self, vacancy_url: str) -> Page:
        pass

    @abstractmethod
    def close_vacancy_tab(self, page: Page) -> None:
        pass

    @abstractmethod
    def response_to_vacancy(
        self, page: Page, response_text: str, random_sleep: Callable
    ) -> None:
        pass
