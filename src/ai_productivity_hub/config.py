from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    llm_provider: str
    openai_api_key: str
    gemini_api_key: str
    groq_api_key: str
    serpapi_api_key: str
    openai_model: str
    gemini_model: str
    groq_model: str

    @property
    def active_model(self) -> str:
        models = {
            "openai": self.openai_model,
            "gemini": self.gemini_model,
            "groq": self.groq_model,
        }
        return models.get(self.llm_provider, self.openai_model)

    @property
    def has_active_api_key(self) -> bool:
        keys = {
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_key,
        }
        return bool(keys.get(self.llm_provider, "").strip())


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    load_dotenv()
    return AppConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "groq").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        serpapi_api_key=os.getenv("SERPAPI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    )
