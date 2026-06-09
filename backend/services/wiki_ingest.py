import hashlib
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from config import settings
from services.wiki_manager import load_alias_index, save_alias_index


STEP1_PROMPT = """You are a music knowledge analyst. Analyze the following song metadata and extract structured information for building a music knowledge base.

Song Metadata:
{metadata}

Extract the following as JSON (output ONLY valid JSON, no markdown fences):
{{
  "song": {{
    "title": "song title",
    "overview": "0-100字歌曲介绍，包含：时长、情绪基调、表达主题、口碑、语言"
  }},
  "artists": [
    {{
      "name": "artist/band name",
      "aliases": [],
      "overview": "0-100字歌手/乐队介绍，包含：籍贯(中国内陆、港台、欧美、日本、韩国等)、出道时间、身份（如：歌手、演员等）、擅长风格（如：摇滚、流行等）、代表作（1-5首即可）"
    }}
  ],
  "albums": [
    {{
      "name": "album name",
      "aliases": [],
      "overview": "0-100字专辑介绍，包含：发表年份、收录歌曲（最出名5首）、专辑主题、代表曲"
    }}
  ],
  "genres": [
    {{
      "name": "genre/style name",
      "aliases": [],
      "overview": "0-100字流派介绍，包含：流派特点、起源、常用乐器、情绪氛围、代表作品、代表歌手"
    }}
  ],
  "connections": [
    {{
      "from": "source entity name",
      "to": "target entity name",
      "type": "performed_by|part_of|similar_style"
    }}
  ]
}}

Rules:
- song overview: describe duration, emotional tone, expressed theme, reputation, language
- artist overview: describe origin, debut time, identity, styles, representative works
- album overview: describe release year, notable tracks, album theme, representative songs
- genre overview: describe characteristics, origin, instruments, mood, representative works/artists
- performed_by: song → artist
- part_of: song → album
- similar_style: artist → genre

常见流派包括：摇滚、流行、电子、嘻哈、R&B、民谣、古典、爵士、DJ（每个流派单独列出，不要合并）

aliases: 列出该实体的已知别名/英文名/简称， 如周杰伦的别名：["周杰伦", "Jay Chou", "周董"]。如果没有别名，输出空数组 []。不要编造不存在的别名。

实体名称规则：
- 所有实体名称（artists/albums/genres 的 name 字段）不能包含特殊字符（/ \\ : * ? " < > |）
- 如果 LLM 输出的名称包含特殊字符，只保留最后一个 / 之后的部分（如 "DJ/DJ舞曲" → "DJ舞曲"）

DJ版/翻唱版本处理规则：
1. 元数据中的 artist 字段大概率是 Bilibili UP主，不一定是歌手
2. 如果标题包含 "DJ版""Remix""翻唱" 等标识：
   a. 优先从标题推断 DJ制作人 或 翻唱歌手（如 "关诗敏《晴天》" → 翻唱歌手是 "关诗敏"）
   b. 如果无法从标题推断，则使用原曲歌手（如 "DJ版《晴天》" → 原曲歌手是 "周杰伦"）
   c. 如果无法推断原曲歌手，则 artists 输出空数组 []
3. 如果无法识别专辑，则 albums 输出空数组 []

Output all text in Chinese
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

## Linked Song
[[{song_meta.get('title', '')}]]
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
    # Must have song with title
    if "song" not in result or not isinstance(result["song"], dict):
        return False
    if "title" not in result["song"]:
        return False

    # Must have connections list
    if "connections" not in result or not isinstance(result["connections"], list):
        return False

    valid_conn_types = {"performed_by", "part_of", "similar_style"}
    for conn in result["connections"]:
        if not all(k in conn for k in ["from", "to", "type"]):
            return False
        if conn["type"] not in valid_conn_types:
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


def resolve_name(llm_name: str, alias_index: Dict[str, List[str]]) -> str:
    """Resolve LLM entity name to canonical name via alias lookup."""
    for canonical, aliases in alias_index.items():
        if llm_name in aliases:
            return canonical
    return llm_name


def _generate_song_entity(song_meta: Dict, analysis: Dict, wiki_dir: str, alias_index: Dict[str, List[str]] = None) -> str:
    """Generate or update song entity page. Returns relative page path."""
    alias_index = alias_index or {}
    today = datetime.now().strftime("%Y-%m-%d")
    title = analysis.get("song", {}).get("title", song_meta.get("title", "unknown"))
    overview = analysis.get("song", {}).get("overview", "")
    if not overview:
        overview = song_meta.get("description", "No description available.")[:200]
    bvid = song_meta.get("bvid", "unknown")
    filepath = os.path.join(wiki_dir, "wiki", "entities", "songs", f"{title}.md")

    # Build links from new schema (resolve names for consistency)
    artist_links = "\n".join(f"- [[{resolve_name(a['name'], alias_index)}]]" for a in analysis.get("artists", []))
    album_links = "\n".join(f"- [[{resolve_name(a['name'], alias_index)}]]" for a in analysis.get("albums", []))
    genre_links = "\n".join(f"- [[{resolve_name(g['name'], alias_index)}]]" for g in analysis.get("genres", []))

    # Fallback: show "Unknown" text (no entity link)
    if not artist_links:
        artist_links = "- Unknown"
    if not album_links:
        album_links = "- Unknown"
    if not genre_links:
        genre_links = "- Unknown"

    if os.path.exists(filepath):
        # Update existing: append BVID to sources
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if bvid not in content:
            content = re.sub(r"(updated:\s*)\S+", rf"\g<1>{today}", content, count=1)
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
{overview}

## Artists
{artist_links or "- Unknown"}

## Album
{album_links or "- Unknown"}

## Genre
{genre_links or "- Unknown"}
"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return os.path.relpath(filepath, wiki_dir)


def _generate_artist_entity(analysis: Dict, song_title: str, wiki_dir: str, alias_index: Dict[str, List[str]] = None, connections: List[Dict] = None) -> List[str]:
    """Create or update artist entity pages. Returns list of relative page paths."""
    alias_index = alias_index or {}
    connections = connections or []
    created = []
    today = datetime.now().strftime("%Y-%m-%d")
    album_names = [resolve_name(a["name"], alias_index) for a in analysis.get("albums", [])]
    genre_names = [resolve_name(g["name"], alias_index) for g in analysis.get("genres", [])]

    for artist in analysis.get("artists", []):
        llm_name = artist["name"]
        name = resolve_name(llm_name, alias_index)
        overview = artist.get("overview", "Extracted from song metadata.")
        filepath = os.path.join(wiki_dir, "wiki", "entities", "artists", f"{name}.md")

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if f"[[{song_title}]]" not in content:
                content = re.sub(r"(updated:\s*)\S+", rf"\g<1>{today}", content, count=1)
                content = _insert_before_next_section(content, "## Songs", f"- [[{song_title}]]")
                for alb in album_names:
                    if f"[[{alb}]]" not in content:
                        content = _insert_before_next_section(content, "## Albums", f"- [[{alb}]]")
                for g in genre_names:
                    if f"[[{g}]]" not in content:
                        content = _insert_before_next_section(content, "## Genre", f"- [[{g}]]")

            # Process connections: performed_by and similar_style
            for conn in connections:
                conn_type = conn.get("type", "")
                if conn_type == "performed_by" and resolve_name(conn.get("to", ""), alias_index) == name:
                    song_ref = resolve_name(conn.get("from", ""), alias_index)
                    if f"[[{song_ref}]]" not in content:
                        content = _insert_before_next_section(content, "## Songs", f"- [[{song_ref}]]")
                elif conn_type == "similar_style" and resolve_name(conn.get("from", ""), alias_index) == name:
                    genre_ref = resolve_name(conn.get("to", ""), alias_index)
                    if f"[[{genre_ref}]]" not in content:
                        content = _insert_before_next_section(content, "## Genre", f"- [[{genre_ref}]]")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            album_links = "\n".join(f"- [[{a}]]" for a in album_names) if album_names else ""
            genre_links = "\n".join(f"- [[{g}]]" for g in genre_names) if genre_names else ""

            content = f"""---
tags: [artist]
created: {today}
updated: {today}
---

# {name}

## Overview
{overview}

## Songs
- [[{song_title}]]

## Albums
{album_links}

## Genre
{genre_links}
"""
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            # Register aliases from LLM output
            aliases = artist.get("aliases", [])
            if aliases:
                if name not in alias_index:
                    alias_index[name] = [name]
                for alias in aliases:
                    if alias != name and alias not in alias_index[name]:
                        alias_index[name].append(alias)

        created.append(os.path.relpath(filepath, wiki_dir))

    return created


def _generate_album_entity(analysis: Dict, song_title: str, wiki_dir: str, alias_index: Dict[str, List[str]] = None, connections: List[Dict] = None) -> List[str]:
    """Create or update album entity pages. Returns list of relative page paths."""
    alias_index = alias_index or {}
    connections = connections or []
    created = []
    today = datetime.now().strftime("%Y-%m-%d")
    artist_names = [resolve_name(a["name"], alias_index) for a in analysis.get("artists", [])]

    for album in analysis.get("albums", []):
        llm_name = album["name"]
        name = resolve_name(llm_name, alias_index)
        overview = album.get("overview", "Extracted from song metadata.")
        filepath = os.path.join(wiki_dir, "wiki", "entities", "albums", f"{name}.md")

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if f"[[{song_title}]]" not in content:
                content = re.sub(r"(updated:\s*)\S+", rf"\g<1>{today}", content, count=1)
                content = _insert_before_next_section(content, "## Songs", f"- [[{song_title}]]")
                for a in artist_names:
                    if f"[[{a}]]" not in content:
                        content = _insert_before_next_section(content, "## Artist", f"- [[{a}]]")

            # Process connections: part_of
            for conn in connections:
                if conn.get("type") == "part_of" and resolve_name(conn.get("to", ""), alias_index) == name:
                    song_ref = resolve_name(conn.get("from", ""), alias_index)
                    if f"[[{song_ref}]]" not in content:
                        content = _insert_before_next_section(content, "## Songs", f"- [[{song_ref}]]")

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
{overview}

## Songs
- [[{song_title}]]

## Artist
{artist_links}
"""
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            # Register aliases from LLM output
            aliases = album.get("aliases", [])
            if aliases:
                if name not in alias_index:
                    alias_index[name] = [name]
                for alias in aliases:
                    if alias != name and alias not in alias_index[name]:
                        alias_index[name].append(alias)

        created.append(os.path.relpath(filepath, wiki_dir))

    return created


def _generate_genre_entity(analysis: Dict, song_title: str, wiki_dir: str, alias_index: Dict[str, List[str]] = None, connections: List[Dict] = None) -> List[str]:
    """Create or update genre entity pages. Returns list of relative page paths."""
    alias_index = alias_index or {}
    connections = connections or []
    created = []
    today = datetime.now().strftime("%Y-%m-%d")
    artist_names = [resolve_name(a["name"], alias_index) for a in analysis.get("artists", [])]

    for genre in analysis.get("genres", []):
        llm_name = genre["name"]
        name = resolve_name(llm_name, alias_index)
        overview = genre.get("overview", "Extracted from song metadata.")
        filepath = os.path.join(wiki_dir, "wiki", "entities", "genres", f"{name}.md")

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if f"[[{song_title}]]" not in content:
                content = re.sub(r"(updated:\s*)\S+", rf"\g<1>{today}", content, count=1)
                content = _insert_before_next_section(content, "## Songs", f"- [[{song_title}]]")
                for a in artist_names:
                    if f"[[{a}]]" not in content:
                        content = _insert_before_next_section(content, "## Artists", f"- [[{a}]]")

            # Process connections: similar_style
            for conn in connections:
                if conn.get("type") == "similar_style" and resolve_name(conn.get("to", ""), alias_index) == name:
                    artist_ref = resolve_name(conn.get("from", ""), alias_index)
                    if f"[[{artist_ref}]]" not in content:
                        content = _insert_before_next_section(content, "## Artists", f"- [[{artist_ref}]]")

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
{overview}

## Songs
- [[{song_title}]]

## Artists
{artist_links}
"""
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            # Register aliases from LLM output
            aliases = genre.get("aliases", [])
            if aliases:
                if name not in alias_index:
                    alias_index[name] = [name]
                for alias in aliases:
                    if alias != name and alias not in alias_index[name]:
                        alias_index[name].append(alias)

        created.append(os.path.relpath(filepath, wiki_dir))

    return created


def _process_orphaned_connections(connections: List[Dict], analysis: Dict, wiki_dir: str, alias_index: Dict[str, List[str]] = None) -> List[str]:
    """Process connections that reference entities not in the current analysis.
    Creates stub files for orphaned entities and returns their paths."""
    alias_index = alias_index or {}
    created = []
    today = datetime.now().strftime("%Y-%m-%d")

    # Collect all entity names already in the analysis
    existing_names = set()
    for a in analysis.get("artists", []):
        existing_names.add(resolve_name(a["name"], alias_index))
    for a in analysis.get("albums", []):
        existing_names.add(resolve_name(a["name"], alias_index))
    for g in analysis.get("genres", []):
        existing_names.add(resolve_name(g["name"], alias_index))

    for conn in connections:
        conn_type = conn.get("type", "")
        from_name = resolve_name(conn.get("from", ""), alias_index)
        to_name = resolve_name(conn.get("to", ""), alias_index)

        if conn_type == "performed_by":
            # song → artist: check if the artist is orphaned
            if to_name not in existing_names:
                filepath = os.path.join(wiki_dir, "wiki", "entities", "artists", f"{to_name}.md")
                if not os.path.exists(filepath):
                    content = f"""---
tags: [artist]
created: {today}
updated: {today}
---

# {to_name}

## Overview
Referenced via connections from {from_name}.

## Songs
- [[{from_name}]]
"""
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                created.append(os.path.relpath(filepath, wiki_dir))
                existing_names.add(to_name)

        elif conn_type == "part_of":
            # song → album: check if the album is orphaned
            if to_name not in existing_names:
                filepath = os.path.join(wiki_dir, "wiki", "entities", "albums", f"{to_name}.md")
                if not os.path.exists(filepath):
                    content = f"""---
tags: [album]
created: {today}
updated: {today}
---

# {to_name}

## Overview
Referenced via connections from {from_name}.

## Songs
- [[{from_name}]]
"""
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                created.append(os.path.relpath(filepath, wiki_dir))
                existing_names.add(to_name)

        elif conn_type == "similar_style":
            # artist → genre: check if the genre is orphaned
            if to_name not in existing_names:
                filepath = os.path.join(wiki_dir, "wiki", "entities", "genres", f"{to_name}.md")
                if not os.path.exists(filepath):
                    content = f"""---
tags: [genre]
created: {today}
updated: {today}
---

# {to_name}

## Overview
Referenced via connections from {from_name}.

## Artists
- [[{from_name}]]
"""
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                created.append(os.path.relpath(filepath, wiki_dir))
                existing_names.add(to_name)

    return created


def _insert_before_next_section(content: str, after_heading: str, new_line: str) -> str:
    """Insert a line after a heading, skipping blank lines, before the first content line."""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == after_heading:
            # Skip blank lines after heading
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            insert_idx = j
            lines.insert(insert_idx, new_line.rstrip("\n"))
            return "\n".join(lines)
    return content


def _update_index_and_log(song_meta: Dict, song_entity_path: str, entity_pages: List[str], wiki_dir: str) -> None:
    """Update index.md and log.md."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Update index.md
    index_path = os.path.join(wiki_dir, "index.md")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        # Add raw song to Raw section
        bvid = song_meta.get("bvid", "")
        if bvid:
            raw_link = f"- [[{bvid}]]\n"
            if raw_link not in index_content:
                index_content = _insert_before_next_section(index_content, "## Raw", raw_link)

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
                ep_normalized = ep.replace("\\", "/")
                if "/artists/" in ep_normalized:
                    index_content = _insert_before_next_section(index_content, "## Artists", entity_link)
                elif "/genres/" in ep_normalized:
                    index_content = _insert_before_next_section(index_content, "## Genres", entity_link)
                elif "/albums/" in ep_normalized:
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
            "song": {"title": song_meta.get("title", ""), "overview": raw_content[:200]},
            "artists": [],
            "albums": [],
            "genres": [],
            "connections": [],
        }
        llm_succeeded = False

    # Validate
    if llm_succeeded and not _validate_step1(analysis):
        llm_succeeded = False

    if not llm_succeeded:
        analysis = {
            "song": {"title": song_meta.get("title", ""), "overview": raw_content[:200]},
            "artists": [],
            "albums": [],
            "genres": [],
            "connections": [],
        }

    # Ensure song title from metadata
    if not analysis.get("song", {}).get("title"):
        analysis.setdefault("song", {})["title"] = song_meta.get("title", "unknown")

    # Step 5: Load alias index
    alias_index = load_alias_index(wiki_dir)

    # Step 6: Generate song entity
    song_entity_path = _generate_song_entity(song_meta, analysis, wiki_dir, alias_index)

    # Step 7: Generate artist/album/genre entities
    title = analysis.get("song", {}).get("title", song_meta.get("title", "unknown"))
    connections = analysis.get("connections", [])
    artist_pages = _generate_artist_entity(analysis, title, wiki_dir, alias_index, connections)
    album_pages = _generate_album_entity(analysis, title, wiki_dir, alias_index, connections)
    genre_pages = _generate_genre_entity(analysis, title, wiki_dir, alias_index, connections)

    orphan_pages = _process_orphaned_connections(connections, analysis, wiki_dir, alias_index)
    all_entity_pages = artist_pages + album_pages + genre_pages + orphan_pages

    # Step 7.5: Rename audio file using LLM-analyzed artist names
    audio_path = song_meta.get("local_file_path", "")
    if audio_path and os.path.exists(audio_path):
        artist_names = [
            resolve_name(a["name"], alias_index)
            for a in analysis.get("artists", [])
        ]
        # Filter out Unknown and empty, take first 3
        artist_names = [a for a in artist_names if a and a != "Unknown"][:3]
        if artist_names:
            artist_part = "+".join(artist_names)
            # Extract title and bvid from original filename
            orig_basename = os.path.basename(audio_path)
            # Parse: {old_artist}-{title}-{bvid}.mp3
            base = orig_basename[:-4] if orig_basename.endswith(".mp3") else orig_basename
            # Extract bvid from end
            bvid_match = re.search(r"[_ ]?(BV[A-Za-z0-9]+)$", base)
            bvid_str = bvid_match.group(1) if bvid_match else ""
            if bvid_match:
                base = base[: -len(bvid_match.group(0))]
            # Split by dash: old_artist-title
            parts = base.split("-", 1)
            title_part = parts[1] if len(parts) >= 2 else parts[0]
            # Build new filename
            new_basename = f"{artist_part}-{title_part}-{bvid_str}.mp3" if bvid_str else f"{artist_part}-{title_part}.mp3"
            new_path = os.path.join(os.path.dirname(audio_path), new_basename)
            try:
                os.rename(audio_path, new_path)
                # Update raw material audio_file_path
                with open(raw_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()
                raw_content = raw_content.replace(
                    f"audio_file_path: {audio_path}",
                    f"audio_file_path: {new_path}",
                )
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(raw_content)
            except OSError:
                pass  # Skip rename on error

    # Step 8: Update index and log
    _update_index_and_log(song_meta, song_entity_path, all_entity_pages, wiki_dir)

    # Step 9: Update cache
    if llm_succeeded:
        _update_cache(raw_path, song_entity_path, wiki_dir)

    # Step 10: Save alias index
    save_alias_index(alias_index, wiki_dir)

    return {
        "status": "ingested",
        "title": song_meta.get("title", ""),
        "song_entity": song_entity_path,
        "entities": len(all_entity_pages),
    }
