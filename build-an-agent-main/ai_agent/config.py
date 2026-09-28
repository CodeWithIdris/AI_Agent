import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized multi-provider configuration for the AI Agent system."""

    PROVIDERS: Dict[str, Dict[str, Any]] = {
        "huggingface": {
            "name": "Hugging Face Router",
            "base_url": "https://router.huggingface.co/v1",
            "env_key": "HF_TOKEN",
            "default_model": "Qwen/Qwen3.8-27B",
            "recommended_models": [
                "Qwen/Qwen3.8-27B",
                "Qwen/Qwen2.5-Coder-32B-Instruct",
                "meta-llama/Llama-3.3-70B-Instruct",
            ],
            "requires_key": True,
        },
        "ollama": {
            "name": "Ollama (Local)",
            "base_url": "http://localhost:11434/v1",
            "env_key": "OLLAMA_API_KEY",
            "default_model": "qwen2.5-coder:7b",
            "recommended_models": [
                "qwen2.5-coder:7b",
                "qwen2.5-coder:14b",
                "llama3.1:8b",
                "deepseek-coder-v2:16b",
                "mistral:7b",
            ],
            "requires_key": False,
        },
        "deepseek": {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "env_key": "DEEPSEEK_API_KEY",
            "default_model": "deepseek-chat",
            "recommended_models": [
                "deepseek-chat",
                "deepseek-coder",
            ],
            "requires_key": True,
        },
        "groq": {
            "name": "Groq Cloud",
            "base_url": "https://api.groq.com/openai/v1",
            "env_key": "GROQ_API_KEY",
            "default_model": "llama-3.3-70b-versatile",
            "recommended_models": [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
            ],
            "requires_key": True,
        },
        "openai": {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "env_key": "OPENAI_API_KEY",
            "default_model": "gpt-4o-mini",
            "recommended_models": [
                "gpt-4o-mini",
                "gpt-4o",
                "o3-mini",
            ],
            "requires_key": True,
        },
    }

    DEFAULT_PROVIDER: str = os.getenv("AGENT_PROVIDER", "huggingface")
    DEFAULT_MODEL: str = os.getenv("AGENT_MODEL", "Qwen/Qwen3.8-27B")
    BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://router.huggingface.co/v1")
    API_KEY: str = (
        os.getenv("HF_TOKEN")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or ""
    )

    MEMORY_FILE: Path = Path(os.getenv("AGENT_MEMORY_FILE", ".agent-memory.json"))
    DEFAULT_WORKSPACE: Path = Path(".")

    @classmethod
    def get_provider_config(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve full provider settings with fallback hierarchy."""
        prov_key = (provider or cls.DEFAULT_PROVIDER).lower()
        preset = cls.PROVIDERS.get(prov_key, {})

        resolved_base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL")
            or preset.get("base_url")
            or "https://api.openai.com/v1"
        )
        resolved_model = (
            model
            or os.getenv("AGENT_MODEL")
            or preset.get("default_model")
            or "gpt-4o-mini"
        )

        env_key_name = preset.get("env_key")
        env_val = os.getenv(env_key_name) if env_key_name else None

        resolved_key = (
            api_key
            or env_val
            or os.getenv("HF_TOKEN")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )

        # Local endpoints don't need real keys
        is_local = "localhost" in resolved_base_url or "127.0.0.1" in resolved_base_url
        if is_local and not resolved_key:
            resolved_key = "ollama-local"

        return {
            "provider": prov_key,
            "base_url": resolved_base_url,
            "model": resolved_model,
            "api_key": resolved_key,
            "is_local": is_local,
            "requires_key": False if is_local else preset.get("requires_key", True),
        }

    @classmethod
    def validate(
        cls,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Validate critical configuration settings, permitting keyless local usage."""
        cfg = cls.get_provider_config(provider=provider, base_url=base_url, api_key=api_key)
        if cfg["requires_key"] and not cfg["api_key"]:
            env_hint = cls.PROVIDERS.get(cfg["provider"], {}).get("env_key", "API_KEY")
            raise ValueError(
                f"API Key is missing for provider '{cfg['provider']}'. "
                f"Please set {env_hint} in your environment or .env file (or switch to Ollama for local offline mode)."
            )

