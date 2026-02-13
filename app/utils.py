import json
import logging
import random
import time
from pathlib import Path

from app.exceptions import LoadingError, SavingError

logger = logging.getLogger(__name__)


def random_sleep(min_seconds: int = 2, max_seconds: int = 5) -> None:
    """Засыпает на случайное время между min_seconds и max_seconds"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def load_json(filepath: str | Path) -> list[str]:
    """Загружает список из JSON файла"""
    path = Path(filepath)
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Файл %s не найден. Возвращается пустой список.", filepath)
        return []
    except PermissionError:
        error_msg = f"Нет прав доступа к файлу: {path}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except IsADirectoryError:
        error_msg = f"Путь ведет к директории, а не файлу: {path}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"Ошибка парсинга JSON в файле {path}: {e}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except UnicodeDecodeError:
        error_msg = f"Ошибка кодировки UTF-8 в файле: {path}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except OSError as e:
        error_msg = f"Ошибка файловой системы при чтении {path}: {e}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except Exception as e:
        error_msg = f"Неизвестная ошибка при чтении {path}: {e}"
        logger.error(error_msg)
        raise LoadingError(error_msg)


def save_json(filepath: str | Path, data: list[str]) -> None:
    """Сохраняет список в JSON файл"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except FileNotFoundError:
        error_msg = f"Файл не найден или невозможно создать: {path}"
        logger.error(error_msg)
        raise SavingError(error_msg)
    except PermissionError:
        error_msg = f"Нет прав на запись файла: {path}"
        logger.error(error_msg)
        raise SavingError(error_msg)
    except IsADirectoryError:
        error_msg = f"Путь ведет к директории, а не файлу: {path}"
        logger.error(error_msg)
        raise SavingError(error_msg)
    except (TypeError, ValueError, RecursionError) as e:
        error_msg = f"Ошибка сериализации JSON: {e}"
        logger.error(error_msg)
        raise SavingError(error_msg)
    except UnicodeEncodeError:
        error_msg = f"Ошибка кодировки Unicode при записи файла: {path}"
        logger.error(error_msg)
        raise SavingError(error_msg)
    except OSError as e:
        error_msg = f"Ошибка файловой системы: {e}"
        logger.error("%s: %s", error_msg, path)
        raise SavingError(f"{error_msg}: {path}")
    except Exception as e:
        error_msg = f"Неизвестная ошибка при записи: {e}"
        logger.error("%s: %s", error_msg, path)
        raise SavingError(f"{error_msg}: {path}")


def load_text_file(filepath: str | Path) -> str:
    """Загружает текст из файла"""
    path = Path(filepath)
    try:
        with path.open("r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        error_msg = f"Файл не найден: {path}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except PermissionError:
        error_msg = f"Нет прав доступа к файлу: {path}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except UnicodeDecodeError:
        error_msg = f"Ошибка кодировки UTF-8 в файле: {path}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except IsADirectoryError:
        error_msg = f"Путь ведет к директории, а не файлу: {path}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
    except Exception as e:
        error_msg = f"Неизвестная ошибка при загрузке файла {path}: {e}"
        logger.error(error_msg)
        raise LoadingError(error_msg)
