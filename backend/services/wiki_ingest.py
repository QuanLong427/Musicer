import hashlib
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings


STEP1_PROMPT = """You are a music knowledge analyst. Analyze the following song metadata and extract structured information.

Song Metadata:
{metadata}

Extract the following as JSON (output ONLY valid JSON, no markdown fences):
{{
  "song_summary": "Brief summary of the song content and background (0-50 words, in Chinese)",
  "artist_info": "Brief artist/band introduction (0-50 words, in Chinese)",
  "album_info": "Brief album introduction (0-50 words, in Chinese, or empty if unknown)",
  "genre_info": "Brief genre/style description (0-50 words, in Chinese, or empty if unknown)",
  "entities": [
    {{
      "name": "entity name",
      "type": "artist|album|genre",
      "relevance": "primary|secondary",
      "confidence": "EXTRACTED|INFERRED|AMBIGUOUS",
      "evidence": "what in the metadata supports this"
    }}
  ],
  "connections": [
    {{
      "from": "source entity name",
      "to": "target entity name",
      "type": "performed_by|part_of|similar_style",
      "confidence": "EXTRACTED|INFERRED|AMBIGUOUS",
      "evidence": "what supports this connection"
    }}
  ]
}}

Rules:
- song_summary: describe the song's content, theme, and writing background
- artist_info: introduce the artist/band's style and significance
- album_info: introduce the album's theme and release background
- genre_info: describe the musical genre characteristics
- artist type: singers, bands, musicians
- album type: music albums, EPs, singles
- genre type: musical styles, genres
- EXTRACTED = directly stated in metadata
- INFERRED = deduced from context
- AMBIGUOUS = unclear or conflicting info
- Include evidence for every entity and connection
- Output all text in Chinese
"""


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _save_raw_material(song_meta: Dict, wiki_dir: str) -> str:
    """Save song metadata as raw material markdown file. Returns file path."""
    bvid = song_meta.get("bvid", "unknown")
    filename = f"{bvid}.md"
    filepath = os.path.join(wiki_dir, "raw", "songs", filename)

    content = f"""---
audio_file_path: {song_meta.get('local_file_path', '')}
bvid: {bvid}
original_title: {song_meta.get('title', '')}
linked_song: {song_meta.get('title', '')}
artist: {song_meta.get('artist', '')}
album: {song_meta.get('album', '')}
genre: {song_meta.get('genre', '')}
url: {song_meta.get('url', '')}
duration: {song_meta.get('duration', 0)}
---

# {song_meta.get('title', '')}

- Artist: {song_meta.get('artist', '')}
- Album: {song_meta.get('album', '')}
- Genre: {song_meta.get('genre', '')}
- Duration: {song_meta.get('duration', 0)}s
- Local File: {song_meta.get('local_file_path', '')}
- Bilibili URL: {song_meta.get('url', '')}
- BVID: {bvid}

## Description
{song_meta.get('description', 'No description available.')}
"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def _check_cache(raw_path: str, wiki_dir: str) -> bool:
    """Check SHA256 cache. Returns True if already cached (duplicate)."""
    cache_path = os.path.join(wiki_dir, ".wiki-cache.json")
    if not os.path.exists(cache_path):
        return False

    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    with open(raw_path, "r", encoding="utf-8") as f:
        content = f.read()

    file_hash = _compute_hash(content)
    rel_path = os.path.relpath(raw_path, wiki_dir)

    if rel_path in cache.get("entries", {}):
        entry = cache["entries"][rel_path]
        if entry.get("hash") == file_hash:
            return True  # HIT - same content

    return False  # MISS


def _update_cache(raw_path: str, song_entity_path: str, wiki_dir: str) -> None:
    """Update the SHA256 cache after successful ingest."""
    cache_path = os.path.join(wiki_dir, ".wiki-cache.json")
    if not os.path.exists(cache_path):
        return

    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    with open(raw_path, "r", encoding="utf-8") as f:
        content = f.read()

    file_hash = _compute_hash(content)
    rel_path = os.path.relpath(raw_path, wiki_dir)

    cache.setdefault("entries", {})[rel_path] = {
        "hash": file_hash,
        "ingested_at": datetime.now().isoformat(),
        "song_entity": song_entity_path,
    }

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _call_llm(prompt: str) -> str:
    """Call OpenAI-compatible LLM API."""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        response = client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")


def _validate_step1(result: Dict) -> bool:
    """Validate Step 1 JSON output structure."""
    required_fields = ["song_summary", "entities", "connections"]
    for field in required_fields:
        if field not in result:
            return False

    if not isinstance(result["entities"], list) or not isinstance(result["connections"], list):
        return False

    valid_confidence = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}
    for entity in result["entities"]:
        if not all(k in entity for k in ["name", "type", "confidence"]):
            return False
        if entity["confidence"] not in valid_confidence:
            return False

    for conn in result["connections"]:
        if not all(k in conn for k in ["from", "to", "type", "confidence"]):
            return False
        if conn["confidence"] not in valid_confidence:
            return False

    return True


def _extract_json(text: str) -> Dict:
    """Extract JSON from LLM response, handling markdown fences."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("No valid JSON found in LLM response")


def _entity_type_to_dir(etype: str) -> str:
    """Map entity type to sub-directory name."""
    mapping = {
        "song": "songs",
        "artist": "artists",
        "genre": "genres",
        "album": "albums",
    }
    return mapping.get(etype, "artists")


def _generate_song_entity(song_meta: Dict, analysis: Dict, wiki_dir: str) -> str:
    """Generate or update song entity page. Returns relative page path."""
    today = datetime.now().strftime("%Y-%m-%d")
    title = song_meta.get("title", "unknown")
    bvid = song_meta.get("bvid", "unknown")
    filepath = os.path.join(wiki_dir, "wiki", "entities", "songs", f"{title}.md")

    # Collect artist/album/genre names from analysis
    artist_names = []
    album_name = ""
    genre_name = ""
    for entity in analysis.get("entities", []):
        if entity["type"] == "artist":
            artist_names.append(entity["name"])
        elif entity["type"] == "album":
            album_name = entity["name"]
        elif entity["type"] == "genre":
            genre_name = entity["name"]

    # Fallback to metadata if LLM didn't extract
    if not artist_names and song_meta.get("artist"):
        artist_names = [song_meta["artist"]]
    if not album_name and song_meta.get("album"):
        album_name = song_meta["album"]
    if not genre_name and song_meta.get("genre"):
        genre_name = song_meta["genre"]

    artist_links = ", ".join(f"[[{a}]]" for a in artist_names) if artist_names else "Unknown"
    album_link = f"[[{album_name}]]" if album_name else "Unknown"
    genre_link = f"[[{genre_name}]]" if genre_name else "Unknown"

    if os.path.exists(filepath):
        # Update existing: append BVID to sources
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if bvid not in content:
            content = re.sub(r"(updated:\s*)\S+", rf"\g<1>{today}", content, count=1)
            # Add bvid to sources list
            if "sources:" in content:
                content = re.sub(
                    r"(sources:\s*\[)([^\]]*)\]",
                    rf"\g<1>\g<2>, {bvid}]",
                    content,
                    count=1,
                )
            else:
                content = re.sub(
                    r"(updated:\s*\S+)",
                    f"sources: [{bvid}]\\n\\1",
                    content,
                    count=1,
                )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        # Create new song entity page
        content = f"""---
tags: [song]
created: {today}
updated: {today}
sources: [{bvid}]
---

# {title}

## Overview
{analysis.get('song_summary', song_meta.get('description', 'No description available.')[:200])}

## Artists
{artist_links}

## Album
{album_link}

## Genre
{genre_link}
"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return os.path.relpath(filepath, wiki_dir)


def _generate_artist_entity(analysis: Dict, song_title: str, album_name: str, wiki_dir: str) -> List[str]:
    """Create or update artist entity pages. Returns list of relative page paths."""
    created = []
    today = datetime.now().strftime("%Y-%m-%d")

    for entity in analysis.get("entities", []):
        if entity["type"] != "artist":
            continue

        name = entity["name"]
        filepath = os.path.join(wiki_dir, "wiki", "entities", "artists", f"{name}.md")

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if f"[[{song_title}]]" not in content:
                content = re.sub(r"(updated:\s*)\S+", rf"\g<1>{today}", content, count=1)
                # Append song to Songs section
                if "## Songs" in content:
                    content = content.replace("## Songs\n", f"## Songs\n- [[{song_title}]]\n")
                # Append album to Albums section if not there
                if album_name and f"[[{album_name}]]" not in content and "## Albums" in content:
                    content = content.replace("## Albums\n", f"## Albums\n- [[{album_name}]]\n")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            genre_name = ""
            for e in analysis.get("entities", []):
                if e["type"] == "genre":
                    genre_name = e["name"]
                    break

            content = f"""---
tags: [artist]
created: {today}
updated: {today}
---

# {name}

## Overview
{entity.get('evidence', 'Extracted from song metadata.')}

## Songs
- [[{song_title}]]

## Albums
- [[{album_name}]] if album_name else ""

## Genre
- [[{genre_name}]] if genre_name else ""
"""
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        created.append(os.path.relpath(filepath, wiki_dir))

    return created


def _generate_album_entity(analysis: Dict, song_title: str, artist_names: List[str], wiki_dir: str) -> List[str]:
    """Create or update album entity pages. Returns list of relative page paths."""
    created = []
    today = datetime.now().strftime("%Y-%m-%d")

    for entity in analysis.get("entities", []):
        if entity["type"] != "album":
            continue

        name = entity["name"]
        filepath = os.path.join(wiki_dir, "wiki", "entities", "albums", f"{name}.md")

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if f"[[{song_title}]]" not in content:
                content = re.sub(r"(updated:\s*)\S+", rf"\g<1>{today}", content, count=1)
                if "## Songs" in content:
                    content = content.replace("## Songs\n", f"## Songs\n- [[{song_title}]]\n")
                for a in artist_names:
                    if f"[[{a}]]" not in content and "## Artist" in content:
                        content = content.replace("## Artist\n", f"## Artist\n- [[{a}]]\n")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            artist_links = "\n".join(f"- [[{a}]]" for a in artist_names) if artist_names else "- Unknown"
            content = f"""---
tags: [album]
created: {today}
updated: {today}
---

# {name}

## Overview
{entity.get('evidence', 'Extracted from song metadata.')}

## Songs
- [[{song_title}]]

## Artist
{artist_links}
"""
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        created.append(os.path.relpath(filepath, wiki_dir))

    return created


def _generate_genre_entity(analysis: Dict, song_title: str, artist_names: List[str], wiki_dir: str) -> List[str]:
    """Create or update genre entity pages. Returns list of relative page paths."""
    created = []
    today = datetime.now().strftime("%Y-%m-%d")

    for entity in analysis.get("entities", []):
        if entity["type"] != "genre":
            continue

        name = entity["name"]
        filepath = os.path.join(wiki_dir, "wiki", "entities", "genres", f"{name}.md")

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if f"[[{song_title}]]" not in content:
                content = re.sub(r"(updated:\s*)\S+", rf"\g<1>{today}", content, count=1)
                if "## Songs" in content:
                    content = content.replace("## Songs\n", f"## Songs\n- [[{song_title}]]\n")
                for a in artist_names:
                    if f"[[{a}]]" not in content and "## Artists" in content:
                        content = content.replace("## Artists\n", f"## Artists\n- [[{a}]]\n")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            artist_links = "\n".join(f"- [[{a}]]" for a in artist_names) if artist_names else "- Unknown"
            content = f"""---
tags: [genre]
created: {today}
updated: {today}
---

# {name}

## Overview
{entity.get('evidence', 'Extracted from song metadata.')}

## Songs
- [[{song_title}]]

## Artists
{artist_links}
"""
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        created.append(os.path.relpath(filepath, wiki_dir))

    return created


def _insert_before_next_section(content: str, after_heading: str, new_line: str) -> str:
    """Insert a line after a heading, before the next section or end of that section."""
    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip() == after_heading:
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## ") or lines[j].startswith("### "):
                    insert_idx = j
                    break
            if insert_idx is None:
                insert_idx = len(lines)
            break
    if insert_idx is not None:
        lines.insert(insert_idx, new_line.rstrip("\n"))
    return "\n".join(lines)


def _update_index_and_log(song_meta: Dict, song_entity_path: str, entity_pages: List[str], wiki_dir: str) -> None:
    """Update index.md and log.md."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Update index.md
    index_path = os.path.join(wiki_dir, "index.md")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        # Add song to Songs section
        song_name = os.path.splitext(os.path.basename(song_entity_path))[0]
        song_link = f"- [[{song_name}]]\n"
        if song_link not in index_content:
            index_content = _insert_before_next_section(index_content, "## Songs", song_link)

        # Add entity pages to their sections
        for ep in entity_pages:
            entity_name = os.path.splitext(os.path.basename(ep))[0]
            entity_link = f"- [[{entity_name}]]\n"
            if entity_link not in index_content:
                if "/artists/" in ep:
                    index_content = _insert_before_next_section(index_content, "## Artists", entity_link)
                elif "/genres/" in ep:
                    index_content = _insert_before_next_section(index_content, "## Genres", entity_link)
                elif "/albums/" in ep:
                    index_content = _insert_before_next_section(index_content, "## Albums", entity_link)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)

    # Update log.md
    log_path = os.path.join(wiki_dir, "log.md")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()

        title = song_meta.get("title") or song_meta.get("bvid", "")
        bvid = song_meta.get("bvid", "")
        log_entry = f"| {today} | ingest | {title} ({bvid}) |\n"
        log_content += log_entry

        with open(log_path, "w", encoding="utf-8") as f:
            f.write(log_content)


def ingest_song(song_meta: Dict, wiki_dir: Optional[str] = None) -> Dict:
    """
    Main ingest entry point. Processes a song through the pipeline.
    This function is synchronous and meant to be called via asyncio.to_thread.
    """
    wiki_dir = wiki_dir or settings.WIKI_DIR

    # Step 1: Save raw material
    raw_path = _save_raw_material(song_meta, wiki_dir)

    # Step 2: Check cache
    if _check_cache(raw_path, wiki_dir):
        return {"status": "cached", "title": song_meta.get("title", "")}

    # Step 3: Read raw material for LLM analysis
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # Step 4: LLM Structured analysis
    prompt = STEP1_PROMPT.format(metadata=raw_content)
    llm_response = _call_llm(prompt)

    try:
        analysis = _extract_json(llm_response)
        llm_succeeded = True
    except (json.JSONDecodeError, ValueError):
        analysis = {
            "song_summary": raw_content[:200],
            "artist_info": "",
            "album_info": "",
            "genre_info": "",
            "entities": [],
            "connections": [],
        }
        llm_succeeded = False

    # Validate
    if llm_succeeded and not _validate_step1(analysis):
        llm_succeeded = False

    if not llm_succeeded:
        analysis = {
            "song_summary": raw_content[:200],
            "artist_info": "",
            "album_info": "",
            "genre_info": "",
            "entities": [],
            "connections": [],
        }

    # Step 5: Generate song entity
    song_entity_path = _generate_song_entity(song_meta, analysis, wiki_dir)

    # Step 6: Generate artist/album/genre entities
    title = song_meta.get("title", "unknown")
    artist_names = [e["name"] for e in analysis.get("entities", []) if e["type"] == "artist"]
    if not artist_names and song_meta.get("artist"):
        artist_names = [song_meta["artist"]]

    album_name = ""
    for e in analysis.get("entities", []):
        if e["type"] == "album":
            album_name = e["name"]
            break
    if not album_name and song_meta.get("album"):
        album_name = song_meta["album"]

    artist_pages = _generate_artist_entity(analysis, title, album_name, wiki_dir)
    album_pages = _generate_album_entity(analysis, title, artist_names, wiki_dir)
    genre_pages = _generate_genre_entity(analysis, title, artist_names, wiki_dir)

    all_entity_pages = artist_pages + album_pages + genre_pages

    # Step 7: Update index and log
    _update_index_and_log(song_meta, song_entity_path, all_entity_pages, wiki_dir)

    # Step 8: Update cache
    if llm_succeeded:
        _update_cache(raw_path, song_entity_path, wiki_dir)

    return {
        "status": "ingested",
        "title": song_meta.get("title", ""),
        "song_entity": song_entity_path,
        "entities": len(all_entity_pages),
    }
