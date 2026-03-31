"""
Returns a LangChain chat model based on the current settings.
Supported providers: gemini, ollama
"""

from config.settings import settings


def get_llm():
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        if not settings.gemini_api_key or settings.gemini_api_key.startswith("your_"):
            raise ValueError(
                "GEMINI_API_KEY is not set.\n"
                "Open .env and add your key, or switch LLM_PROVIDER=ollama."
            )
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=settings.temperature,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.temperature,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'.\n"
            "Valid values are 'gemini' or 'ollama'."
        )
