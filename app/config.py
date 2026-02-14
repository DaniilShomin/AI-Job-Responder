from typing import TypedDict

from dotenv import load_dotenv
import os

load_dotenv()


class Settings(TypedDict, total=False):
    """Настройки приложения"""

    api_key: str
    model: str
    hh_search_url: str | None
    habr_search_url: str | None
    headless: bool
    timeout: int
    data_file: str
    resume_file: str
    prompt_file: str


def get_settings() -> Settings:
    """Получение настроек из переменных окружения"""
    from app.exceptions import ValidationError

    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValidationError("API_KEY не установлен в переменных окружения")

    settings: Settings = {
        "api_key": api_key,
        "model": os.getenv("MODEL", "stepfun/step-3.5-flash:free"),
        "hh_search_url": os.getenv("HH_SEARCH_URL"),
        "habr_search_url": os.getenv("HABR_SEARCH_URL"),
        "headless": os.getenv("HEADLESS", "true").lower() == "true",
        "timeout": int(os.getenv("TIMEOUT", "10")),
        "data_file": os.getenv("DATA_FILE", "data.json"),
        "resume_file": os.getenv("RESUME_FILE", "resume.txt"),
        "prompt_file": os.getenv("PROMPT_FILE", "prompt.txt"),
    }
    return settings


settings = get_settings()
