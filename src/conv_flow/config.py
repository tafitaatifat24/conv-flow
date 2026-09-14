"""Configuration and settings for conv-flow application."""
import os
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "conv-flow"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database settings
    database_url: str = "sqlite:///./conv_flow.db"
    database_echo: bool = False

    # LLM Provider settings
    llm_provider: Literal["openai", "anthropic", "gemini", "local"] = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-sonnet-20240229"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    local_llm_url: str = "http://localhost:11434"
    local_llm_model: str = "mistral"

    # LLM behavior settings
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    llm_timeout_seconds: int = 60

    # API settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    
    # LinkedIn integration settings
    linkedin_enabled: bool = False
    encryption_key: str = "dev-key-change-in-production"  # Use strong key in production

    @model_validator(mode="after")
    def sync_gemini_to_openai_key(self):
        """
        Sync GEMINI_API_KEY environment variable to OPENAI_API_KEY.
        If OPENAI_API_KEY is not set but GEMINI_API_KEY is, use GEMINI_API_KEY value.
        """
        # Check if OPENAI_API_KEY is empty but GEMINI_API_KEY is set in environment
        if not self.openai_api_key:
            gemini_key_env = os.environ.get("GEMINI_API_KEY", "")
            if gemini_key_env:
                self.openai_api_key = gemini_key_env
        
        return self

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
