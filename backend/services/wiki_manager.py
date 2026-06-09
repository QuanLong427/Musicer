import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import PROJECT_ROOT, settings

WIKI_TEMPLATE_DIR = PROJECT_ROOT / "template" / "wiki"


def _ensure_dirs(wiki_dir: str) -> None:
    """Create all required wiki subdirectories."""
    dirs = [
        os.path.join(wiki_dir, "raw", "songs"),
        os.path.join(wiki_dir, "wiki", "entities", "songs"),
        os.path.join(wiki_dir, "wiki", "entities", "artists"),
        os.path.join(wiki_dir, "wiki", "entities", "genres"),
        os.path.join(wiki_dir, "wiki", "entities", "albums"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def _ensure_file(path: str, content: str) -> None:
    """Write file only if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def init_wiki(wiki_dir: Optional[str] = None) -> Dict:
    """Initialize the wiki directory structure by copying from template."""
    wiki_dir = wiki_dir or settings.WIKI_DIR
    wiki_path = Path(wiki_dir)

    if wiki_path.exists() and os.path.exists(os.path.join(wiki_dir, ".wiki-schema.md")):
        return {"status": "already_initialized", "wiki_dir": wiki_dir}

    _ensure_dirs(wiki_dir)

    # Copy template files to wiki directory
    created_date = datetime.now().strftime("%Y-%m-%d")
    for tpl_file in WIKI_TEMPLATE_DIR.iterdir():
        if tpl_file.is_file() and not tpl_file.name.startswith("."):
            dest = os.path.join(wiki_dir, tpl_file.name)
            if not os.path.exists(dest):
                content = tpl_file.read_text(encoding="utf-8")
                content = content.replace("{created}", created_date)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)

    # Copy .wiki-schema.md (hidden file)
    schema_tpl = WIKI_TEMPLATE_DIR / ".wiki-schema.md"
    schema_dest = os.path.join(wiki_dir, ".wiki-schema.md")
    if schema_tpl.exists() and not os.path.exists(schema_dest):
        content = schema_tpl.read_text(encoding="utf-8")
        content = content.replace("{created}", created_date)
        with open(schema_dest, "w", encoding="utf-8") as f:
            f.write(content)

    # Write .wiki-cache.json
    cache_path = os.path.join(wiki_dir, ".wiki-cache.json")
    _ensure_file(cache_path, json.dumps({"version": 1, "entries": {}}, indent=2))

    return {"status": "initialized", "wiki_dir": wiki_dir}


def get_wiki_status(wiki_dir: Optional[str] = None) -> Dict:
    """Return wiki initialization status and statistics."""
    wiki_dir = wiki_dir or settings.WIKI_DIR
    schema_path = os.path.join(wiki_dir, ".wiki-schema.md")

    if not os.path.exists(schema_path):
        return {"initialized": False}

    songs_dir = os.path.join(wiki_dir, "wiki", "entities", "songs")
    artists_dir = os.path.join(wiki_dir, "wiki", "entities", "artists")
    genres_dir = os.path.join(wiki_dir, "wiki", "entities", "genres")
    albums_dir = os.path.join(wiki_dir, "wiki", "entities", "albums")

    def count_md_files(d: str) -> int:
        if not os.path.exists(d):
            return 0
        return len([f for f in os.listdir(d) if f.endswith(".md")])

    # Find last ingested time from log.md
    last_ingested = None
    log_path = os.path.join(wiki_dir, "log.md")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if line.startswith("|") and "ingest" in line.lower():
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2 and parts[1]:
                        last_ingested = parts[1]
                        break

    return {
        "initialized": True,
        "wiki_dir": wiki_dir,
        "total_songs": count_md_files(songs_dir),
        "total_artists": count_md_files(artists_dir),
        "total_genres": count_md_files(genres_dir),
        "total_albums": count_md_files(albums_dir),
        "last_ingested_at": last_ingested,
    }


def load_alias_index(wiki_dir: Optional[str] = None) -> Dict[str, List[str]]:
    """Load alias-index.json. Returns empty dict if not found."""
    wiki_dir = wiki_dir or settings.WIKI_DIR
    alias_path = os.path.join(wiki_dir, "alias-index.json")

    if not os.path.exists(alias_path):
        return {}

    with open(alias_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_alias_index(alias_index: Dict[str, List[str]], wiki_dir: Optional[str] = None) -> None:
    """Write alias_index dict to alias-index.json."""
    wiki_dir = wiki_dir or settings.WIKI_DIR
    alias_path = os.path.join(wiki_dir, "alias-index.json")

    with open(alias_path, "w", encoding="utf-8") as f:
        json.dump(alias_index, f, indent=2, ensure_ascii=False)
