"""
system_init.py — Auto-initialize all data directories and files on startup.
"""

import shutil
import logging
from pathlib import Path

from config import settings, PROJECT_ROOT

logger = logging.getLogger(__name__)

MEMORY_DATA_DIR = PROJECT_ROOT / "memory" / "data"
TEMPLATE_DIR = PROJECT_ROOT / "memory" / "template"
TEMPLATE_PROFILE = TEMPLATE_DIR / "user_profile.md"
DATA_PROFILE = MEMORY_DATA_DIR / "user_profile.md"
HISTORY_FILE = MEMORY_DATA_DIR / "history.jsonl"


def init_system_files():
    """Initialize all data directories and files on server startup."""
    logger.info("[system-init] Checking data directories...")

    # 1. Ensure memory/data/ exists
    MEMORY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"[system-init] Memory data dir: {MEMORY_DATA_DIR}")

    # 2. Ensure history.jsonl exists with metadata
    if not HISTORY_FILE.exists():
        import json
        from datetime import datetime, timezone
        metadata = {
            "type": "metadata",
            "dream_offset": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        HISTORY_FILE.write_text(json.dumps(metadata, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info("[system-init] Created history.jsonl with metadata")
    else:
        logger.info("[system-init] history.jsonl already exists")

    # 3. Ensure user_profile.md exists (copy from template)
    if not DATA_PROFILE.exists():
        if TEMPLATE_PROFILE.exists():
            shutil.copy2(TEMPLATE_PROFILE, DATA_PROFILE)
            logger.info("[system-init] Copied profile template to data directory")
        else:
            logger.warning(f"[system-init] Template not found: {TEMPLATE_PROFILE}")
    else:
        logger.info("[system-init] user_profile.md already exists")

    # 4. Ensure db/scenario.yml exists
    from services.scenario_manager import _ensure_file as ensure_scenario
    ensure_scenario()
    logger.info("[system-init] scenario.yml checked")

    # 5. Ensure LLM-Wiki/ directory exists (lightweight check)
    wiki_dir = settings.WIKI_DIR
    if not Path(wiki_dir).exists():
        logger.info(f"[system-init] Wiki dir not found: {wiki_dir} (call POST /api/wiki/init to create)")
    else:
        logger.info(f"[system-init] Wiki dir exists: {wiki_dir}")

    logger.info("[system-init] System initialization complete")
