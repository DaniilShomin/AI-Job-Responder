import logging
import random
import time

import requests
from requests.exceptions import Timeout, RequestException

from app.exceptions import OpenAIError

logger = logging.getLogger(__name__)


class AIClient:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def get_response(self, message: str, system_prompt: str | None = None) -> str:
        """Получение ответа от AI модели с retry и exponential backoff."""

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": message})

        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
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
                last_exception = e
                logger.warning(
                    "Таймаут при запросе к AI API (попытка %s/%s): %s",
                    attempt,
                    self.max_retries,
                    e,
                )
                if attempt < self.max_retries:
                    sleep_time = self.retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    time.sleep(sleep_time)
                continue
            except RequestException as e:
                last_exception = e
                logger.warning(
                    "Ошибка запроса к AI API (попытка %s/%s): %s",
                    attempt,
                    self.max_retries,
                    e,
                )
                if attempt < self.max_retries:
                    sleep_time = self.retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    time.sleep(sleep_time)
                continue

            if response.status_code != 200:
                try:
                    data = response.json()
                    error_message = data.get("error", {}).get(
                        "message", "Неизвестная ошибка"
                    )
                except Exception:
                    error_message = response.text

                logger.error(
                    "AI API вернул статус %s: %s",
                    response.status_code,
                    error_message,
                )

                # Retry на 5xx и 429
                if response.status_code >= 500 or response.status_code == 429:
                    last_exception = OpenAIError(
                        f"Ошибка AI API (статус {response.status_code}): {error_message}"
                    )
                    if attempt < self.max_retries:
                        sleep_time = self.retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                        logger.info("Повторная попытка через %.2f сек...", sleep_time)
                        time.sleep(sleep_time)
                    continue

                raise OpenAIError(
                    f"Ошибка AI API (статус {response.status_code}): {error_message}"
                )

            try:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError) as e:
                logger.error("Ошибка при обработке ответа от AI API: %s", e)
                raise OpenAIError(f"Ошибка при обработке ответа от AI API: {e}") from e

        # Если исчерпаны все попытки
        if isinstance(last_exception, Timeout):
            raise TimeoutError(
                f"AI API не отвечает в течение {self.timeout} секунд после {self.max_retries} попыток"
            ) from last_exception

        raise OpenAIError(
            f"Ошибка при запросе к AI API после {self.max_retries} попыток: {last_exception}"
        ) from last_exception
