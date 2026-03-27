from __future__ import annotations

import time
from openai import OpenAI, APIError

from financial_report_decode.config import settings


class LlmClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        api_key = api_key or settings.llm_api_key
        if not api_key:
            raise ValueError("LLM_API_KEY or MGALLERY_API_KEY is required for LLM analysis")
        self.client = OpenAI(api_key=api_key, base_url=base_url or settings.llm_base_url)
        self.model = model or settings.llm_model

    def complete(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
        last_exception = None
        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": user_prompt}],
                        },
                    ],
                    extra_body={
                        "chat_template_kwargs": {"thinking": settings.llm_enable_thinking},
                    },
                    stream=False,
                )
                return completion.choices[0].message.content or ""
            except APIError as exc:
                last_exception = exc
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    time.sleep(wait_time)
                continue
        raise last_exception or RuntimeError("LLM request failed after retries")
