"""LLM provider factory for creating LangChain ChatModel instances."""
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from conv_flow.config import settings


def get_llm_model() -> Any:
    """
    Factory function to create and return the appropriate LangChain ChatModel.
    
    Returns:
        BaseChatModel: Configured LangChain chat model based on settings
        
    Raises:
        ValueError: If LLM provider is not configured or API key is missing
    """
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )
    
    elif settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )
    
    elif settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        return ChatGoogleGenerativeAI(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )
    
    elif settings.llm_provider == "local":
        # For local LLMs via Ollama or similar
        # This would use langchain_community.chat_models
        raise NotImplementedError(
            "Local LLM support not yet implemented. "
            "Please install langchain-community and configure local LLM endpoint."
        )
    
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def get_structured_llm(model: Any, schema: Any) -> Any:
    """
    Wrap a LangChain ChatModel to return structured output using a Pydantic schema.
    
    Args:
        model: The LangChain ChatModel to wrap
        schema: Pydantic model class for structured output
        
    Returns:
        Configured model with structured output
    """
    return model.with_structured_output(schema)
