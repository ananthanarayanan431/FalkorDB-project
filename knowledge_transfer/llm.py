"""Chat model factory. Same provider selection as the sample chatbot, kept here so
this package does not depend on demo code."""
import os

from langchain_openai import ChatOpenAI


def default_llm() -> ChatOpenAI | None:
    """OpenRouter when OPENROUTER_API_KEY is set, else OpenAI; None when neither key is set."""
    if key := os.getenv("OPENROUTER_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
        )
    return None
