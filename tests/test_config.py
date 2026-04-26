import os

import pytest

from app.config import get_settings, Settings
from app.exceptions import ValidationError


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_settings_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(ValidationError, match="API_KEY"):
        get_settings()


def test_get_settings_success(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("MODEL", "test-model")
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("TIMEOUT", "20")
    monkeypatch.setenv("RESPONSE_LIMIT_PER_PLATFORM", "5")

    settings = get_settings()
    assert settings.api_key == "test-key"
    assert settings.api_base_url == "https://routerai.ru/api/v1"
    assert settings.model == "test-model"
    assert settings.headless is False
    assert settings.timeout == 20
    assert settings.hh_search_url is None
    assert settings.response_limit_per_platform == 5


def test_get_settings_uses_defaults(monkeypatch):
    monkeypatch.setenv("API_KEY", "key")
    monkeypatch.delenv("MODEL", raising=False)
    monkeypatch.delenv("HEADLESS", raising=False)
    monkeypatch.delenv("TIMEOUT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RESPONSE_LIMIT_PER_PLATFORM", raising=False)
    settings = get_settings()
    assert settings.api_base_url == "https://routerai.ru/api/v1"
    assert settings.model == "stepfun/step-3.5-flash:free"
    assert settings.headless is True
    assert settings.timeout == 10
    assert settings.database_url == "sqlite:///vacancies.db"
    assert settings.response_limit_per_platform == 10


def test_get_settings_empty_limit_is_none(monkeypatch):
    monkeypatch.setenv("API_KEY", "key")
    monkeypatch.setenv("RESPONSE_LIMIT_PER_PLATFORM", "")
    settings = get_settings()
    assert settings.response_limit_per_platform is None


def test_get_settings_cached(monkeypatch):
    monkeypatch.setenv("API_KEY", "cached-key")
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
