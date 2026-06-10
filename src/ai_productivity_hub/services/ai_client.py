from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent

from ai_productivity_hub.config import AppConfig


class AIClientError(RuntimeError):
    """Raised when an AI request cannot be completed."""


@dataclass
class AIMessage:
    role: str
    content: str


class AIClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.config.has_active_api_key:
            raise AIClientError(
                f"Missing API key for provider '{self.config.llm_provider}'. Add it to your .env file."
            )

        provider = self.config.llm_provider
        if provider == "openai":
            return self._generate_openai(system_prompt, user_prompt, temperature)
        if provider == "gemini":
            return self._generate_gemini(system_prompt, user_prompt, temperature)
        if provider == "groq":
            return self._generate_groq(system_prompt, user_prompt, temperature)
        raise AIClientError(f"Unsupported LLM provider: {provider}")

    def try_generate(self, system_prompt: str, user_prompt: str, fallback: str, temperature: float = 0.2) -> str:
        try:
            return self.generate(system_prompt, user_prompt, temperature)
        except Exception:
            return fallback

    def _generate_openai(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.config.openai_api_key)
        response = client.responses.create(
            model=self.config.openai_model,
            temperature=temperature,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output_text.strip()

    def _generate_gemini(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.config.gemini_api_key)
        model = genai.GenerativeModel(self.config.gemini_model, system_instruction=system_prompt)
        response = model.generate_content(
            user_prompt,
            generation_config={"temperature": temperature},
        )
        return (response.text or "").strip()

    def _generate_groq(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        from groq import Groq

        client = Groq(api_key=self.config.groq_api_key)
        response = client.chat.completions.create(
            model=self.config.groq_model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()


def structured_report_prompt(task: str, body: str) -> tuple[str, str]:
    system = dedent(
        """
        You are a precise productivity assistant.
        Return concise, structured Markdown with clear section headings.
        Be factual and avoid filler.
        """
    ).strip()
    user = f"Task: {task}\n\nContent:\n{body}"
    return system, user
