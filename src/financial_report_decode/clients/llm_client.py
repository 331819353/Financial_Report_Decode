from __future__ import annotations

from openai import OpenAI

from financial_report_decode.config import settings


class LlmClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        api_key = api_key or settings.dashscope_api_key
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY is required for LLM analysis")
        self.client = OpenAI(api_key=api_key, base_url=base_url or settings.dashscope_base_url)
        self.model = model or settings.llm_model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            extra_body={"enable_thinking": settings.llm_enable_thinking},
            stream=False,
        )
        return completion.choices[0].message.content or ""

