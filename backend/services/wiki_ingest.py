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
  "source_summary": "Brief summary of the song (1-2 sentences)",
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
- artist type: singers, bands, musicians
- album type: music albums, EPs, singles
- genre type: musical styles, genres
- EXTRACTED = directly stated in metadata
- INFERRED = deduced from context
- AMBIGUOUS = unclear or conflicting info
- Include evidence for every entity and connection
"""


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _save_raw_material(song_meta: Dict, wiki_dir: str) -> str:
    """Save song metadata as raw material markdown file. Returns file path."""
    today = datetime.now().strftime("%Y-%m-%d")
    bvid = song_meta.get("bvid", "unknown")
    filename = f"{today}-{bvid}.md"
    filepath = os.path.join(wiki_dir, "raw", "songs", filename)

    content = f"""---
title: {song_meta.get('title', '')}
artist: {song_meta.get('artist', '')}
bvid: {bvid}
local_file_path: {song_meta.get('local_file_path', '')}
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


def _update_cache(raw_path: str, source_page: str, wiki_dir: str) -> None:
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
        "source_page": source_page,
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
    required_fields = ["source_summary", "entities", "connections"]
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
    # Try to find JSON in code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Try to find raw JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("No valid JSON found in LLM response")


def _generate_source_page(song_meta: Dict, analysis: Dict, wiki_dir: str) -> str:
    """Generate the source summary wiki page. Returns page path."""
    today = datetime.now().strftime("%Y-%m-%d")
    bvid = song_meta.get("bvid", "unknown")
    filename = f"{today}-{bvid}.md"
    filepath = os.path.join(wiki_dir, "wiki", "sources", filename)

    # Build entity links
    entity_links = []
    for entity in analysis.get("entities", []):
        etype = entity["type"]
        name = entity["name"]
        if etype == "artist":
            entity_links.append(f"- Artist: [[{name}]]")
        elif etype == "album":
            entity_links.append(f"- Album: [[{name}]]")
        elif etype == "genre":
            entity_links.append(f"- Genre: [[{name}]]")

    entities_text = "\n".join(entity_links) if entity_links else "- No entities extracted"

    content = f"""---
tags: [song, source]
created: {today}
updated: {today}
bvid: {bvid}
local_file_path: {song_meta.get('local_file_path', '')}
---

# {song_meta.get('title', '')}

## Overview
{analysis.get('source_summary', 'No summary available.')}

## Metadata
- Artist: {song_meta.get('artist', '')}
- Album: {song_meta.get('album', '')}
- Genre: {song_meta.get('genre', '')}
- Duration: {song_meta.get('duration', 0)}s
- Local File: {song_meta.get('local_file_path', '')}

## Key Facts
{entities_text}

## Connections
"""
    for conn in analysis.get("connections", []):
        content += f"- {conn['from']} --[{conn['type']}]--> {conn['to']} ({conn['confidence']})\n"

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return os.path.relpath(filepath, wiki_dir)


def _entity_type_to_dir(etype: str) -> str:
    """Map entity type to sub-directory name."""
    mapping = {
        "artist": "artists",
        "genre": "genres",
        "album": "albums",
    }
    return mapping.get(etype, "artists")


def _generate_entity_pages(analysis: Dict, source_page: str, wiki_dir: str) -> List[str]:
    """Create or update entity pages. Returns list of page paths."""
    created = []
    today = datetime.now().strftime("%Y-%m-%d")

    for entity in analysis.get("entities", []):
        name = entity["name"]
        etype = entity["type"]
        subdir = _entity_type_to_dir(etype)
        filepath = os.path.join(wiki_dir, "wiki", "entities", subdir, f"{name}.md")

        if os.path.exists(filepath):
            # Update existing: append source reference
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Add source to sources list in frontmatter if not already there
            source_ref = os.path.basename(source_page).replace(".md", "")
            if source_ref not in content:
                # Update the `updated:` field in frontmatter via regex
                content = re.sub(
                    r"(updated:\s*)\S+",
                    rf"\g<1>{today}",
                    content,
                    count=1,
                )
                # Add source to sources list if not present
                if "sources:" not in content:
                    content = re.sub(
                        r"(updated:\s*\S+)",
                        f"sources: [{source_ref}]\\n\\1",
                        content,
                        count=1,
                    )
                # Append to bottom
                content += f"\n- [[{source_ref}]]\n"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            # Create new entity page
            content = f"""---
tags: [{etype}]
created: {today}
updated: {today}
---

# {name}

## Overview
{entity.get('evidence', 'Extracted from song metadata.')}

## Confidence
{entity.get('confidence', 'UNKNOWN')}

## Sources
- [[{os.path.basename(source_page).replace('.md', '')}]]
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
            # Find the end of this section (next ## or ### heading, or end of file)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## ") or lines[j].startswith("### "):
                    insert_idx = j
                    break
            if insert_idx is None:
                # End of file — insert before last empty line or at end
                insert_idx = len(lines)
            break
    if insert_idx is not None:
        lines.insert(insert_idx, new_line.rstrip("\n"))
    return "\n".join(lines)


def _update_index_and_log(song_meta: Dict, source_page: str, entity_pages: List[str], wiki_dir: str) -> None:
    """Update index.md and log.md."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Update index.md
    index_path = os.path.join(wiki_dir, "index.md")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        source_link = f"- [[{os.path.basename(source_page).replace('.md', '')}]] - {song_meta.get('title') or song_meta.get('bvid', '')}\n"
        if source_link not in index_content:
            index_content = index_content.replace("## Sources\n", f"## Sources\n{source_link}")

        for ep in entity_pages:
            entity_name = os.path.splitext(os.path.basename(ep))[0]
            entity_link = f"- [[{entity_name}]]\n"
            if entity_link not in index_content:
                # Insert before the next section heading (## or ###)
                if "/artists/" in ep:
                    index_content = _insert_before_next_section(index_content, "### Artists", entity_link)
                elif "/genres/" in ep:
                    index_content = _insert_before_next_section(index_content, "### Genres", entity_link)
                elif "/albums/" in ep:
                    index_content = _insert_before_next_section(index_content, "### Albums", entity_link)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)

    # Update log.md
    log_path = os.path.join(wiki_dir, "log.md")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()

        log_entry = f"| {today} | ingest | {song_meta.get('title') or song_meta.get('bvid', '')} ({song_meta.get('bvid', '')}) |\n"
        log_content += log_entry

        with open(log_path, "w", encoding="utf-8") as f:
            f.write(log_content)


def ingest_song(song_meta: Dict, wiki_dir: Optional[str] = None) -> Dict:
    """
    Main ingest entry point. Processes a song through the two-step pipeline.
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

    # Step 4: LLM Step 1 - Structured analysis
    prompt = STEP1_PROMPT.format(metadata=raw_content)
    llm_response = _call_llm(prompt)

    try:
        analysis = _extract_json(llm_response)
        llm_succeeded = True
    except (json.JSONDecodeError, ValueError):
        # Fallback: simplified processing
        analysis = {
            "source_summary": raw_content[:500],
            "entities": [],
            "connections": [],
        }
        llm_succeeded = False

    # Validate Step 1
    if llm_succeeded and not _validate_step1(analysis):
        llm_succeeded = False

    if not llm_succeeded:
        analysis = {
            "source_summary": raw_content[:500],
            "entities": [],
            "connections": [],
        }

    # Step 5: Generate wiki pages
    source_page = _generate_source_page(song_meta, analysis, wiki_dir)
    entity_pages = _generate_entity_pages(analysis, source_page, wiki_dir)

    # Step 6: Update index and log
    _update_index_and_log(song_meta, source_page, entity_pages, wiki_dir)

    # Step 7: Update cache (only if LLM succeeded, so retry is possible)
    if llm_succeeded:
        _update_cache(raw_path, source_page, wiki_dir)

    return {
        "status": "ingested",
        "title": song_meta.get("title", ""),
        "source_page": source_page,
        "entities": len(entity_pages),
    }
