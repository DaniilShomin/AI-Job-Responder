import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

from app.exceptions import ValidationError

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Настройки приложения"""

    api_key: str
    api_base_url: str
    model: str
    hh_search_url: str | None
    habr_search_url: str | None
    headless: bool
    timeout: int
    login_timeout: int
    data_file: str
    resume_file: str
    prompt_file: str
    response_limit_per_platform: int | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Получение настроек из переменных окружения"""
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValidationError("API_KEY не установлен в переменных окружения")

    response_limit_raw = os.getenv("RESPONSE_LIMIT_PER_PLATFORM")
    if response_limit_raw == "":
        response_limit_per_platform = None
    elif response_limit_raw is None:
        response_limit_per_platform = 10
    else:
        response_limit_per_platform = int(response_limit_raw)

    return Settings(
        api_key=api_key,
        api_base_url=os.getenv("API_BASE_URL", "https://routerai.ru/api/v1"),
        model=os.getenv("MODEL", "stepfun/step-3.5-flash:free"),
        hh_search_url=os.getenv("HH_SEARCH_URL"),
        habr_search_url=os.getenv("HABR_SEARCH_URL"),
        headless=os.getenv("HEADLESS", "true").lower() == "true",
        timeout=int(os.getenv("TIMEOUT", "10")),
        login_timeout=int(os.getenv("LOGIN_TIMEOUT", "60000")),
        data_file=os.getenv("DATA_FILE", "data.json"),
        resume_file=os.getenv("RESUME_FILE", "resume.txt"),
        prompt_file=os.getenv("PROMPT_FILE", "prompt.txt"),
        response_limit_per_platform=response_limit_per_platform,
    )
