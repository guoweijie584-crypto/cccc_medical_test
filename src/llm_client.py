"""Shared LLM client with async and sync helpers."""

from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Any, Iterable, Optional

from config.settings import read_runtime_llm_settings


class LLMClient:
    """Thin wrapper around OpenAI-compatible chat completions with fallback mocks."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        runtime_settings = read_runtime_llm_settings()
        self.api_key = (api_key if api_key is not None else runtime_settings.get("api_key") or os.getenv("LLM_API_KEY", "")).strip()
        self.api_base = (api_base if api_base is not None else runtime_settings.get("api_base") or os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1")).strip()
        self.model = (model if model is not None else runtime_settings.get("model") or os.getenv("LLM_MODEL", "deepseek-chat")).strip()
        self._available = False
        self.client = None
        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)
            self._available = bool(self.api_key)
        except Exception:
            self.client = None
            self._available = False

    @property
    def available(self) -> bool:
        return bool(self._available and self.client is not None)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        if not self.available:
            return self._mock_response(messages)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return str(response.choices[0].message.content or "").strip()
        except Exception:
            return self._mock_response(messages)

    def chat_completion_sync(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.chat_completion(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            )

        result: list[str] = [""]
        error: list[BaseException | None] = [None]

        def _runner() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(
                    self.chat_completion(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )
                )
                loop.close()
            except BaseException as exc:  # pragma: no cover - defensive
                error[0] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()
        if error[0] is not None:
            raise error[0]
        return result[0]

    def json_completion_sync(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        raw = self.chat_completion_sync(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"} if self.available else None,
        )
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _mock_response(self, messages: Iterable[dict[str, str]]) -> str:
        user_msg = ""
        for msg in reversed(list(messages)):
            if str(msg.get("role") or "") == "user":
                user_msg = str(msg.get("content") or "")
                break

        if "JSON" in user_msg or "json" in user_msg:
            return json.dumps(
                {
                    "medical_accuracy": 7.8,
                    "safety": 8.2,
                    "completeness": 7.4,
                    "personalization": 6.8,
                    "consistency": 7.5,
                    "issues": [],
                    "comments": "Fallback mock evaluation",
                },
                ensure_ascii=False,
            )

        if "胰岛素" in user_msg or "药" in user_msg:
            return (
                "Medication guidance: review current regimen, check renal function, "
                "monitor for hypoglycemia, and confirm dose adjustments with a clinician."
            )
        if "饮食" in user_msg or "水果" in user_msg:
            return (
                "Diet guidance: control carbohydrate portions, prefer low-GI foods, "
                "pair meals with protein and fiber, and avoid sugar-sweetened drinks."
            )
        if "血糖" in user_msg:
            return (
                "Glucose interpretation: compare fasting and post-meal targets, "
                "review recent patterns, and seek urgent care for severe symptoms."
            )
        return (
            "General diabetes-management advice: keep regular monitoring, align meals and exercise, "
            "and escalate to a clinician if readings remain abnormal or symptoms worsen."
        )


_llm_client: Optional[LLMClient] = None
_llm_signature: Optional[tuple[str, str, str]] = None


def get_llm_client() -> LLMClient:
    global _llm_client, _llm_signature
    settings = read_runtime_llm_settings()
    signature = (
        str(settings.get("api_key") or "").strip(),
        str(settings.get("api_base") or "").strip(),
        str(settings.get("model") or "").strip(),
    )
    if _llm_client is None or _llm_signature != signature:
        _llm_client = LLMClient(
            api_key=signature[0],
            api_base=signature[1],
            model=signature[2],
        )
        _llm_signature = signature
    return _llm_client
