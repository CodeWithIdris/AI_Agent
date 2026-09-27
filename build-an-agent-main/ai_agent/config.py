import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration for the AI Agent system."""

    DEFAULT_MODEL: str = os.getenv("AGENT_MODEL", "Qwen/Qwen3.8-27B")
    BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://router.huggingface.co/v1")
    API_KEY: str = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY", "")

    MEMORY_FILE: Path = Path(os.getenv("AGENT_MEMORY_FILE", ".agent-memory.json"))
    DEFAULT_WORKSPACE: Path = Path(".")

    @classmethod
    def validate(cls):
        """Validate critical configuration settings."""
        if not cls.API_KEY:
            raise ValueError(
                "API Key is missing. Please set HF_TOKEN or OPENAI_API_KEY in your environment or .env file."
            )
