class OpenAIError(Exception):
    """Исключение, возникающее при ошибках взаимодействия с OpenAI API."""

    pass


class VacancyProcessingError(Exception):
    """Исключение, возникающее при ошибках обработки вакансий."""

    pass


class BrowserError(Exception):
    """Исключение, возникающее при ошибках браузера или автоматизации."""

    pass


class ValidationError(Exception):
    """Исключение, возникающее при ошибках валидации данных."""

    pass


class LoadingError(Exception):
    """Исключение, возникающее при ошибках загрузки данных из файлов."""

    pass


class SavingError(Exception):
    """Исключение, возникающее при ошибках сохранения данных в файлы."""

    pass


class ScraperError(Exception):
    """Исключение, возникающее при ошибках скрейпинга данных."""

    pass
