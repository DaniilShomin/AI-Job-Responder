from playwright.sync_api import sync_playwright

from .hh_scraper import HHVacancyScraper
from .config import Settings


class BrowserContext:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.playwright = None
        self.browser = None
        self.context = None
        self.scraper = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.settings["headless"]
        )
        try:
            self.context = self.browser.new_context(storage_state="auth_state.json")
        except Exception:
            self.context = self.browser.new_context()

        page = self.context.new_page()
        self.scraper = HHVacancyScraper(page=page)
        return self.scraper

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.context:
                self.context.storage_state(path="auth_state.json")
        finally:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
