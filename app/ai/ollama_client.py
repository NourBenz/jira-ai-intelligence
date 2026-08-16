import json
from typing import TypeVar

import requests
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from app.schemas.ai import AIAnswerContent
from app.schemas.rag import RAGAnswerContent

StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def answer(self, system_prompt: str, user_prompt: str) -> AIAnswerContent:
        return self._structured_answer(system_prompt, user_prompt, AIAnswerContent)

    def answer_rag(self, system_prompt: str, user_prompt: str) -> RAGAnswerContent:
        return self._structured_answer(system_prompt, user_prompt, RAGAnswerContent)

    def _structured_answer(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredResponse],
    ) -> StructuredResponse:
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "format": response_model.model_json_schema(),
                    "options": {"temperature": 0},
                },
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["message"]["content"]
            return response_model.model_validate_json(content)
        except requests.exceptions.Timeout as error:
            raise HTTPException(504, "The local AI model timed out.") from error
        except requests.exceptions.ConnectionError as error:
            raise HTTPException(503, "The local AI service is unavailable.") from error
        except (
            requests.exceptions.RequestException,
            KeyError,
            json.JSONDecodeError,
            ValidationError,
        ) as error:
            raise HTTPException(502, "The local AI returned an invalid response.") from error
