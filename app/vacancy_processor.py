import logging
import re

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
            logger.error("Ошибка загрузки резюме из файла %s", resume_path)
            raise
        try:
            self.prompt_template = load_text_file(prompt_path)
        except LoadingError:
            logger.error("Ошибка загрузки шаблона из файла %s", prompt_path)
            raise

    def is_correct_profession(self, vacancy_description: str) -> bool:
        """Проверяет, относится ли вакансия к нужной профессии"""
        professions_str = ", ".join(self.CORRECT_PROFESSIONS)
        message = (
            f"Определи, относится ли следующая вакансия к профессии {professions_str}. "
            f"И подходит для junior или middle уровня. "
            f"Если относится, ответь строго одним словом 'да', иначе строго одним словом 'нет'.\n\n{vacancy_description}"
        )
        try:
            response = self.ai_client.get_response(message).strip().lower()
            return re.fullmatch(r"да[!?.]?", response) is not None
        except (TimeoutError, OpenAIError) as e:
            logger.error("Ошибка при определении профессии вакансии: %s", e)
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
            logger.error("Ошибка при генерации отклика на вакансию: %s", e)
            raise
