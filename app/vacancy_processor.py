import logging

from app.ai import AIClient
from app.exceptions import OpenAIError, LoadingError
from app.utils import load_text_file

logger = logging.getLogger(__name__)


class VacancyProcessor:
    CORRECT_PROFESSIONS = [
        "python developer",
        "python разработчик",
        "python программист",
        "backend developer на python",
        "backend разработчик на python",
        "backend программист на python",
    ]

    def __init__(self, ai_client: AIClient, resume_path: str, prompt_path: str) -> None:
        self.ai_client = ai_client
        try:
            self.resume = load_text_file(resume_path)
        except LoadingError:
            logger.error(f"Ошибка загрузки резюме из файла {resume_path}")
            raise
        try:
            self.prompt_template = load_text_file(prompt_path)
        except LoadingError:
            logger.error(f"Ошибка загрузки шаблона из файла {prompt_path}")
            raise

    def is_correct_profession(self, vacancy_description: str) -> bool:
        """Проверяет, относится ли вакансия к нужной профессии"""
        professions_str = ", ".join(self.CORRECT_PROFESSIONS)
        message = (
            f"Определи, относится ли следующая вакансия к профессии {professions_str}. "
            f"Если относится, ответь строго 'да', иначе 'нет'.\n\n{vacancy_description}"
        )
        try:
            response = self.ai_client.get_response(message).strip().lower()
            return "да" in response
        except (TimeoutError, OpenAIError) as e:
            logger.error(f"Ошибка при определении профессии вакансии: {e}")
            raise

    def generate_response(self, vacancy_title: str, vacancy_description: str) -> str:
        """Генерирует отклик на вакансию"""
        full_text = f"Заголовок вакансии: {vacancy_title}\n\nОписание вакансии: {vacancy_description}"
        message = (
            f"Напиши краткий отклик на эту вакансию:\n{full_text}\n\n"
            f"Мое резюме:\n{self.resume}\n\n"
            f"Пример отклика:\n{self.prompt_template}\n\n"
            f"Сформируй отклик по вышеуказанному плану."
        )
        try:
            return self.ai_client.get_response(message)
        except (TimeoutError, OpenAIError) as e:
            logger.error(f"Ошибка при генерации отклика на вакансию: {e}")
            raise
