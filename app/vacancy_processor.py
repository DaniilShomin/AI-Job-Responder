import logging
import re
from functools import lru_cache

from app.ai import AIClient
from app.exceptions import OpenAIError, LoadingError
from app.utils import load_text_file

logger = logging.getLogger(__name__)


class VacancyProcessor:
    def __init__(
        self,
        ai_client: AIClient,
        resume_path: str,
        prompt_path: str,
        correct_professions: list[str] | None = None,
        grade_levels: list[str] | None = None,
    ) -> None:
        self.ai_client = ai_client
        self.correct_professions = correct_professions
        self.grade_levels = grade_levels
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
        """Проверяет, относится ли вакансия к нужной профессии и грейду."""
        if not self.correct_professions and not self.grade_levels:
            return True
        return self._check_profession(vacancy_description)

    @lru_cache(maxsize=128)
    def _check_profession(self, vacancy_description: str) -> bool:
        conditions = []
        if self.correct_professions:
            professions_str = ", ".join(self.correct_professions)
            conditions.append(f"относится ли к профессии {professions_str}")
        if self.grade_levels:
            grades_str = " или ".join(self.grade_levels)
            conditions.append(f"подходит для {grades_str} уровня")

        query = " и ".join(conditions)
        system_prompt = (
            "Ты помощник для фильтрации вакансий. "
            "Отвечай строго одним словом: 'да' или 'нет'. Никаких пояснений."
        )
        message = (
            f"Определи, {query} следующая вакансия. "
            f"Если да, ответь строго одним словом 'да', иначе строго одним словом 'нет'.\n\n"
            f"{vacancy_description}"
        )
        try:
            response = (
                self.ai_client.get_response(message, system_prompt=system_prompt)
                .strip()
                .lower()
            )
            return re.fullmatch(r"да[!?.]?", response) is not None
        except (TimeoutError, OpenAIError) as e:
            logger.error("Ошибка при определении профессии вакансии: %s", e)
            raise

    def generate_response(self, vacancy_title: str, vacancy_description: str) -> str:
        """Генерирует отклик на вакансию."""
        return self._generate_response_cached(vacancy_title, vacancy_description)

    @lru_cache(maxsize=128)
    def _generate_response_cached(self, vacancy_title: str, vacancy_description: str) -> str:
        full_text = f"Заголовок вакансии: {vacancy_title}\n\nОписание вакансии: {vacancy_description}"
        system_prompt = (
            "Ты карьерный консультант. "
            "Пишешь краткие, убедительные сопроводительные письма на вакансии."
        )
        message = (
            f"Напиши краткий отклик на эту вакансию:\n{full_text}\n\n"
            f"Мое резюме:\n{self.resume}\n\n"
            f"Пример отклика:\n{self.prompt_template}\n\n"
            f"Сформируй отклик по вышеуказанному плану."
        )
        try:
            return self.ai_client.get_response(message, system_prompt=system_prompt)
        except (TimeoutError, OpenAIError) as e:
            logger.error("Ошибка при генерации отклика на вакансию: %s", e)
            raise
