from playwright.sync_api import sync_playwright

from .base_scraper import BaseScraper
from .config import Settings


class BrowserContext:
    def __init__(self, settings: Settings, scraper: type[BaseScraper]):
        self.settings = settings
        self.playwright = None
        self.browser = None
        self.context = None
        self.scraper = scraper

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.settings.headless
        )
        try:
            self.context = self.browser.new_context(storage_state="auth_state.json")
        except Exception:
            self.context = self.browser.new_context()

        page = self.context.new_page()
        page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "font", "media"]
            else route.continue_(),
        )
        scraper = self.scraper(page=page)
        return scraper

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.context:
                self.context.storage_state(path="auth_state.json")
        finally:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
