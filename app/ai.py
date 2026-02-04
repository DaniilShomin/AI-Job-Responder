import logging
import requests
from requests.exceptions import Timeout, RequestException

from app.exceptions import OpenAIError

logger = logging.getLogger(__name__)


class AIClient:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str, model: str, timeout: int = 10):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def get_response(self, message: str, system_prompt: str | None = None) -> str:
        """Получение ответа от AI модели"""

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": message})

        try:
            response = requests.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "messages": messages},
                timeout=self.timeout,
            )
        except Timeout as e:
            logger.error(f"Таймаут при запросе к AI API: {e}")
            raise TimeoutError(
                f"AI API не отвечает в течение {self.timeout} секунд"
            ) from e
        except RequestException as e:
            logger.error(f"Ошибка при запросе к AI API: {e}")
            raise OpenAIError(f"Ошибка при запросе к AI API: {e}") from e

        if response.status_code != 200:
            try:
                data = response.json()
                error_message = data.get("error", {}).get(
                    "message", "Неизвестная ошибка"
                )
            except Exception:
                error_message = response.text

            logger.error(
                f"AI API вернут статус {response.status_code}: {error_message}"
            )
            raise OpenAIError(
                f"Ошибка AI API (статус {response.status_code}): {error_message}"
            )

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Ошибка при обработке ответа от AI API: {e}")
            raise OpenAIError(f"Ошибка при обработке ответа от AI API: {e}") from e
