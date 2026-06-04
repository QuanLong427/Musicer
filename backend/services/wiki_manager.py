import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import PROJECT_ROOT, settings


WIKI_SCHEMA_TEMPLATE = """# .wiki-schema.md

## Metadata
- topic: Music Knowledge Base
- created: {created}
- language: zh
- version: 1.0

## Directory Structure
- `raw/songs/` - Raw song metadata (immutable)
- `wiki/sources/` - Source summary pages (one per song)
- `wiki/entities/artists/` - Artist/band entity pages
- `wiki/entities/genres/` - Genre/style entity pages
- `wiki/entities/albums/` - Album entity pages
- `wiki/topics/` - Topic pages (cross-song themes)
- `index.md` - Master index
- `log.md` - Operation log

## Entity Types
- `song` - A music track
- `artist` - Singer or band
- `album` - Music album
- `genre` - Musical style/genre

## Relationship Types
- `performed_by` - Song performed by artist
- `part_of` - Song/album belongs to larger collection
- `similar_style` - Similar musical style

## Alias Table
- 摇滚 = rock = rock music
- 流行 = pop = pop music
- 电子 = electronic = edm
- 嘻哈 = hip-hop = rap
- R&B = rhythm and blues
- 民谣 = folk
- 古典 = classical
- 爵士 = jazz
"""


def _ensure_dirs(wiki_dir: str) -> None:
    """Create all required wiki subdirectories."""
    dirs = [
        os.path.join(wiki_dir, "raw", "songs"),
        os.path.join(wiki_dir, "wiki", "sources"),
        os.path.join(wiki_dir, "wiki", "entities", "artists"),
        os.path.join(wiki_dir, "wiki", "entities", "genres"),
        os.path.join(wiki_dir, "wiki", "entities", "albums"),
        os.path.join(wiki_dir, "wiki", "topics"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def _ensure_file(path: str, content: str) -> None:
    """Write file only if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def init_wiki(wiki_dir: Optional[str] = None) -> Dict:
    """Initialize the wiki directory structure. Returns status dict."""
    wiki_dir = wiki_dir or settings.WIKI_DIR
    wiki_path = Path(wiki_dir)

    if wiki_path.exists() and os.path.exists(os.path.join(wiki_dir, ".wiki-schema.md")):
        return {"status": "already_initialized", "wiki_dir": wiki_dir}

    _ensure_dirs(wiki_dir)

    # Write .wiki-schema.md
    schema_path = os.path.join(wiki_dir, ".wiki-schema.md")
    _ensure_file(schema_path, WIKI_SCHEMA_TEMPLATE.format(
        created=datetime.now().strftime("%Y-%m-%d")
    ))

    # Write .wiki-cache.json
    cache_path = os.path.join(wiki_dir, ".wiki-cache.json")
    _ensure_file(cache_path, json.dumps({"version": 1, "entries": {}}, indent=2))

    # Write index.md
    index_path = os.path.join(wiki_dir, "index.md")
    _ensure_file(index_path, "# Music Knowledge Base Index\n\n## Sources\n\n## Entities\n\n### Artists\n\n### Genres\n\n### Albums\n\n## Topics\n")

    # Write log.md
    log_path = os.path.join(wiki_dir, "log.md")
    _ensure_file(log_path, "# Operation Log\n\n| Date | Action | Details |\n|------|--------|---------|\n")

    # Write purpose.md
    purpose_path = os.path.join(wiki_dir, "purpose.md")
    _ensure_file(purpose_path, "# Purpose\n\n## Research Direction\nBuild a structured knowledge base of music metadata for personalized recommendations.\n\n## Key Questions\n- What genres and artists does the user prefer?\n- What are the relationships between songs, artists, and albums?\n- How do listening patterns evolve over time?\n")

    return {"status": "initialized", "wiki_dir": wiki_dir}


def get_wiki_status(wiki_dir: Optional[str] = None) -> Dict:
    """Return wiki initialization status and statistics."""
    wiki_dir = wiki_dir or settings.WIKI_DIR
    schema_path = os.path.join(wiki_dir, ".wiki-schema.md")

    if not os.path.exists(schema_path):
        return {"initialized": False}

    sources_dir = os.path.join(wiki_dir, "wiki", "sources")
    artists_dir = os.path.join(wiki_dir, "wiki", "entities", "artists")
    genres_dir = os.path.join(wiki_dir, "wiki", "entities", "genres")
    albums_dir = os.path.join(wiki_dir, "wiki", "entities", "albums")
    topics_dir = os.path.join(wiki_dir, "wiki", "topics")

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
        "total_songs": count_md_files(sources_dir),
        "total_artists": count_md_files(artists_dir),
        "total_genres": count_md_files(genres_dir),
        "total_albums": count_md_files(albums_dir),
        "total_topics": count_md_files(topics_dir),
        "last_ingested_at": last_ingested,
    }


def read_schema_aliases(wiki_dir: Optional[str] = None) -> Dict[str, List[str]]:
    """Read alias table from .wiki-schema.md for query expansion."""
    wiki_dir = wiki_dir or settings.WIKI_DIR
    schema_path = os.path.join(wiki_dir, ".wiki-schema.md")
    aliases: Dict[str, List[str]] = {}

    if not os.path.exists(schema_path):
        return aliases

    with open(schema_path, "r", encoding="utf-8") as f:
        in_alias_section = False
        for line in f:
            if line.strip() == "## Alias Table":
                in_alias_section = True
                continue
            if in_alias_section and line.startswith("## "):
                break
            if in_alias_section and "=" in line:
                parts = [p.strip() for p in line.strip().split("=")]
                if len(parts) >= 2:
                    for part in parts:
                        aliases[part.lower()] = parts

    return aliases
