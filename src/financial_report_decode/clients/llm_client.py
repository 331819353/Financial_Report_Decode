from __future__ import annotations

from openai import OpenAI

from financial_report_decode.config import settings


class LlmClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        api_key = api_key or settings.llm_api_key
        if not api_key:
            raise ValueError("LLM_API_KEY or MGALLERY_API_KEY is required for LLM analysis")
        self.client = OpenAI(api_key=api_key, base_url=base_url or settings.llm_base_url)
        self.model = model or settings.llm_model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
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
