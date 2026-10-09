"""Chat model factory (OpenRouter). Kept here so this package does not depend on demo code."""
from langchain_openai import ChatOpenAI

from knowledge_transfer.core.config import get_settings


def default_llm() -> ChatOpenAI | None:
    """An OpenRouter chat model, or None when OPENROUTER_API_KEY is not set."""
    settings = get_settings()
    if key := settings.openrouter_api_key:
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
        )
    return None
