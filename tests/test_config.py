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

    settings = get_settings()
    assert settings.api_key == "test-key"
    assert settings.api_base_url == "https://routerai.ru/api/v1"
    assert settings.model == "test-model"
    assert settings.headless is False
    assert settings.timeout == 20
    assert settings.hh_search_url is None


def test_get_settings_uses_defaults(monkeypatch):
    monkeypatch.setenv("API_KEY", "key")
    monkeypatch.delenv("MODEL", raising=False)
    monkeypatch.delenv("HEADLESS", raising=False)
    monkeypatch.delenv("TIMEOUT", raising=False)
    monkeypatch.delenv("DATA_FILE", raising=False)
    settings = get_settings()
    assert settings.api_base_url == "https://routerai.ru/api/v1"
    assert settings.model == "stepfun/step-3.5-flash:free"
    assert settings.headless is True
    assert settings.timeout == 10
    assert settings.data_file == "data.json"


def test_get_settings_cached(monkeypatch):
    monkeypatch.setenv("API_KEY", "cached-key")
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
