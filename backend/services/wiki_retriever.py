"""
wiki_retriever.py — Layer 1: Hardcoded search engine for LLM-Wiki.

This module does NOT call any LLM. It performs:
1. Read index.md — fixed path, fixed structure
2. Alias expansion — from .wiki-schema.md alias table
3. Grep search — keyword search across wiki/ directory
4. Ranking — filename exact > index entry > body keyword count
5. Read 3-5 pages — truncate if > 2000 chars

The LLM (main agent) handles Layer 2: semantic understanding and synthesis.
"""

import os
import re
from typing import Dict, List, Optional

from config import settings
from services.wiki_manager import read_schema_aliases


MAX_PAGES = 5
MAX_PAGE_CHARS = 2000
TRUNCATE_FRONT = 500


def _read_index(wiki_dir: str) -> str:
    """Read index.md content. Returns empty string if not found."""
    index_path = os.path.join(wiki_dir, "index.md")
    if not os.path.exists(index_path):
        return ""
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


def _expand_aliases(keyword: str, aliases: Dict[str, List[str]]) -> set:
    """
    Expand keyword using alias table.
    Rule: A=B means A and B are equivalent. No transitive expansion (A=B, B=C does NOT imply A=C).
    """
    terms = {keyword.lower()}
    keyword_lower = keyword.lower()

    for alias_key, alias_group in aliases.items():
        if keyword_lower in [a.lower() for a in alias_group]:
            # Found keyword in this alias group — add all members
            for a in alias_group:
                terms.add(a.lower())

    return terms


def _grep_search(wiki_path: str, search_terms: set) -> List[Dict]:
    """
    Search all .md files in wiki/ directory.
    Returns list of {path, name, content, filename_score, body_score, matched_lines}.
    """
    results = []

    for root, _, files in os.walk(wiki_path):
        for fname in files:
            if not fname.endswith(".md"):
                continue

            fpath = os.path.join(root, fname)
            name_without_ext = os.path.splitext(fname)[0]

            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            filename_score = 0
            body_score = 0
            matched_lines = []

            # Check filename match
            for term in search_terms:
                if term in name_without_ext.lower():
                    filename_score = 100
                    break

            # Check body matches
            content_lower = content.lower()
            for term in search_terms:
                count = content_lower.count(term)
                if count > 0:
                    body_score += count * 10
                    # Collect matching lines
                    for line in content.split("\n"):
                        if term in line.lower():
                            matched_lines.append(line.strip()[:200])

            if filename_score > 0 or body_score > 0:
                results.append({
                    "path": fpath,
                    "name": name_without_ext,
                    "content": content,
                    "filename_score": filename_score,
                    "body_score": body_score,
                    "matched_lines": matched_lines[:5],  # cap at 5 lines
                })

    return results


def _rank_results(
    grep_results: List[Dict],
    index_content: str,
    search_terms: set,
) -> List[Dict]:
    """
    Rank results by priority:
    1. Filename exact match (100)
    2. Index entry match (80)
    3. Body keyword count
    """
    for r in grep_results:
        score = r["filename_score"]

        # Check index.md for this page
        if score == 0:
            link_pattern = f"[[{r['name']}]]"
            if link_pattern in index_content:
                # Check if search term appears near this link
                idx = index_content.find(link_pattern)
                context = index_content[max(0, idx - 100):idx + len(link_pattern) + 100].lower()
                for term in search_terms:
                    if term in context:
                        score = 80
                        break
                if score == 0:
                    score = 60  # link exists but no keyword in context

        if score == 0:
            score = r["body_score"]

        r["score"] = score

    grep_results.sort(key=lambda x: x["score"], reverse=True)
    return grep_results


def _truncate_page(content: str) -> str:
    """
    Truncate page content if > MAX_PAGE_CHARS.
    Strategy: frontmatter + first 500 chars + matched paragraphs.
    """
    if len(content) <= MAX_PAGE_CHARS:
        return content

    lines = content.split("\n")

    # Extract frontmatter
    frontmatter_end = 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                frontmatter_end = i + 1
                break

    frontmatter = "\n".join(lines[:frontmatter_end])

    # Get first 500 chars of body
    body = "\n".join(lines[frontmatter_end:])
    body_preview = body[:TRUNCATE_FRONT]

    return f"{frontmatter}\n\n{body_preview}\n\n... [truncated, {len(content)} chars total]"


def retrieve(query: str, wiki_dir: Optional[str] = None) -> str:
    """
    Main retrieval function — Layer 1 (hardcoded, no LLM).

    Args:
        query: User's search query
        wiki_dir: Path to wiki directory

    Returns:
        Formatted string with top 3-5 relevant pages for LLM to read.
    """
    wiki_dir = wiki_dir or settings.WIKI_DIR
    wiki_path = os.path.join(wiki_dir, "wiki")

    if not os.path.exists(wiki_path):
        return "[Wiki not initialized or empty]"

    # Step 1: Read index.md
    index_content = _read_index(wiki_dir)

    # Step 2: Alias expansion
    aliases = read_schema_aliases(wiki_dir)
    search_terms = _expand_aliases(query, aliases)

    # Step 3: Grep search
    grep_results = _grep_search(wiki_path, search_terms)

    if not grep_results:
        return f"[No results found for '{query}' in wiki]"

    # Step 4: Rank results
    ranked = _rank_results(grep_results, index_content, search_terms)

    # Step 5: Read top 3-5 pages (truncate if too long)
    top_pages = ranked[:MAX_PAGES]
    output_parts = []

    for page in top_pages:
        truncated = _truncate_page(page["content"])
        output_parts.append(
            f"=== {page['name']} (score: {page.get('score', 0)}, "
            f"matched: {len(page['matched_lines'])} lines) ===\n{truncated}"
        )

    return f"Found {len(ranked)} matches. Top {len(top_pages)} pages:\n\n" + "\n\n".join(output_parts)


def retrieve_structured(query: str, wiki_dir: Optional[str] = None) -> List[Dict]:
    """
    Retrieve structured search results for HTTP API.

    Args:
        query: User's search query
        wiki_dir: Path to wiki directory

    Returns:
        List of dicts with title, path, snippet, score.
    """
    wiki_dir = wiki_dir or settings.WIKI_DIR
    wiki_path = os.path.join(wiki_dir, "wiki")

    if not os.path.exists(wiki_path):
        return []

    index_content = _read_index(wiki_dir)
    aliases = read_schema_aliases(wiki_dir)
    search_terms = _expand_aliases(query, aliases)
    grep_results = _grep_search(wiki_path, search_terms)

    if not grep_results:
        return []

    ranked = _rank_results(grep_results, index_content, search_terms)

    return [
        {
            "title": r["name"],
            "path": os.path.relpath(r["path"], wiki_dir),
            "snippet": r["matched_lines"][0] if r["matched_lines"] else "",
            "score": r.get("score", 0),
        }
        for r in ranked[:MAX_PAGES]
    ]
