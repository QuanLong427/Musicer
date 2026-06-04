import os
import sys
from pathlib import Path

# Project root is the parent of the backend/ directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Platform detection
IS_WINDOWS: bool = sys.platform == "win32"
PLATFORM_HINT: str = "Windows" if IS_WINDOWS else "Linux"


def _resolve_music_dir() -> str:
    raw = os.getenv("MUSIC_DIR", "Documents/bili")
    p = Path(raw)
    if p.is_absolute():
        return str(p)
    return str(PROJECT_ROOT / p)


def _resolve_wiki_dir() -> str:
    raw = os.getenv("WIKI_DIR", "LLM-Wiki")
    p = Path(raw)
    if p.is_absolute():
        return str(p)
    return str(PROJECT_ROOT / p)


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv(
        "OPENAI_BASE_URL", "https://api.deepseek.com"
    )
    MODEL_NAME: str = os.getenv("MODEL_NAME", "deepseek-chat")
    MUSIC_DIR: str = _resolve_music_dir()
    WIKI_DIR: str = _resolve_wiki_dir()
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DREAM_INTERVAL_HOURS: int = int(os.getenv("DREAM_INTERVAL_HOURS", "24"))


settings = Settings()
