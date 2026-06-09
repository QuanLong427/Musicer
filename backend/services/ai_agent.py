import json
import os
import subprocess
from typing import Any, AsyncGenerator, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

import logging

from config import settings, IS_WINDOWS, PLATFORM_HINT, PROJECT_ROOT
from services.skill_loader import discover_skills, load_skill
from services.memory_manager import append_history, read_profile
from services.wiki_manager import load_alias_index
from services.wiki_ingest import resolve_name

logger = logging.getLogger(__name__)


def _find_bash() -> str:
    """Find Git Bash on Windows, fall back to system bash."""
    import shutil
    import sys

    if sys.platform == "win32":
        # 1. Try to find bash via git.exe location (most reliable)
        git_exe = shutil.which("git")
        if git_exe:
            git_dir = os.path.dirname(os.path.dirname(git_exe))
            candidate = os.path.join(git_dir, "bin", "bash.exe")
            if os.path.isfile(candidate):
                return candidate
            # Also check usr/bin/bash.exe (Git for Windows 2.x+)
            candidate = os.path.join(git_dir, "usr", "bin", "bash.exe")
            if os.path.isfile(candidate):
                return candidate

        # 2. Try common install locations
        for base in [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]:
            candidate = os.path.join(base, "Git", "bin", "bash.exe")
            if os.path.isfile(candidate):
                return candidate

        # 3. Search PATH for bash in Git directories (avoid WSL bash)
        for p in os.environ.get("PATH", "").split(os.pathsep):
            if "git" in p.lower() and os.path.isfile(os.path.join(p, "bash.exe")):
                return os.path.join(p, "bash.exe")

    return shutil.which("bash") or "bash"


def _to_unix_path(win_path: str) -> str:
    """Convert a Windows path to Git Bash compatible /c/... format. No-op on Linux."""
    if not IS_WINDOWS:
        return win_path
    # Try cygpath first (available in Git Bash)
    try:
        result = subprocess.run(
            ["cygpath", win_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Manual fallback: C:\foo\bar → /c/foo/bar
    p = win_path.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].lower()
        p = "/" + drive + p[2:]
    return p

# ── System Prompts ──────────────────────────────────────────────────────────

_BASE_PROMPT = """你是 Musicer 的 AI 音频助手。保持简洁的中文终端风格语气。

## 重要限制
- **必须使用提供的工具**：`local_search`、`bili_search`、`convert_video`、`bash`、`read_file`、`wiki_search`，禁止自行拼接 curl 命令
- 禁止使用 WebSearch、WebFetch 或任何网络搜索工具
- **严禁**安装任何外部工具或依赖（如 pip install、npm install -g、brew install 等），遇到工具缺失或命令失败时，如实告知用户并停止操作，等待用户指示

## 路由规则

路由优先级：**知识库查询 → 本地优先 → 云端兜底 → 转换收尾**

0. **知识库查询**（用户问音乐知识、偏好、历史、推荐但未指定具体歌名时）→ 先用 `wiki_search` 搜索知识库
   - 有结果 → 基于知识库内容回答，仅在用户明确要求播放时才用 `local_search` 搜索歌曲
   - 无结果 → 跳过，走正常流程
1. **播放/搜索请求**：必须先用 `local_search` 搜索本地曲库
   - 本地有结果（total > 0）→ 直接推荐本地文件，**严禁调用 convert_video 或 bili_search**
   - 本地无结果（total = 0）→ 切换到云端搜索
2. **用户明确说"云端/B站/网上搜索"** → 跳过本地搜索，直接用 `bili_search`
3. **转换**：仅在云端搜索找到结果后，作为收尾步骤将资源添加到本地
   - **严禁**在未搜索云端的情况下直接调用 convert_video

## wiki_search 使用场景（调用即触发子 Agent）
**触发条件**（必须调用 `wiki_search`）：
- 用户问音乐知识、偏好、历史、推荐，但**未指定具体歌名**
- 示例："我平时喜欢听什么风格" → `wiki_search("风格偏好")`
- 示例："推荐一些摇滚" → `wiki_search("摇滚")`（仅当用户明确要求播放时才调用 `local_search`）
- 示例："推荐三首歌给我" → `wiki_search("推荐英伦摇滚或华语流行，偏好Coldplay和Oasis")`（根据上方用户画像中的偏好信息构造 query）

**非触发条件**（不要调用 `wiki_search`）：
- 用户明确说"播放XX"、指定歌名 → 直接走播放流程
- 用户只是闲聊、打招呼 → 不调用任何搜索工具"""

# ── Output Format ─────────────────────────────────────────────────────────

_OUTPUT_FORMAT = """

## 推荐输出格式（严格遵守）

当向用户推荐歌曲时，先用自然语言简要介绍，然后 **必须** 将曲目放在独立的 tracks 代码块中。格式如下：

本地搜索结果（必须包含 filename 和 bvid 字段）：
```tracks
[
  {"id":"xxx","title":"歌名","author":"歌手","url":"/audio/xxx.mp3","filename":"歌手-歌名-BV1xxxxx.mp3","bvid":"BV1xxxxx"},
  {"id":"yyy","title":"歌名2","author":"歌手2","url":"/audio/yyy.mp3","filename":"歌手2-歌名2-BV2yyyyy.mp3","bvid":"BV2yyyyy"}
]
```

云端搜索结果（必须包含 bvid 字段）：
```tracks
[
  {"bvid":"BV1xxxxx","title":"视频标题","author":"UP主","duration":"4:32","url":"https://www.bilibili.com/video/BV1xxxxx"},
  {"bvid":"BV2yyyyy","title":"视频标题2","author":"UP主2","duration":"12:05","url":"https://www.bilibili.com/video/BV2yyyyy"}
]
```

关键规则：
1. 代码块标记必须用 ```tracks 开头，``` 结尾，各占独立一行
2. 数据必须是合法 JSON 数组，**逐字复制** API 返回的 JSON 字段值，**严禁修改、缩短、重写或"美化"任何字段**
3. 本地结果每个对象必须包含 id、title、author、url、filename、bvid 六个字段（bvid 可能为空字符串或 null）
4. 云端结果每个对象必须包含 bvid、title、author、duration、url 五个字段
5. 即使只推荐一首歌也要用此格式
6. 不要把 tracks 代码块放在其他 markdown 代码块内
7. 如果用户只是闲聊、提问，不需要输出 tracks 代码块
8. title 字段必须与 API 返回值完全一致，即使很长或包含下划线等字符也不能删减"""


def _build_system_prompt(scenario: str = "默认") -> str:
    """Build system prompt with all skills loaded. LLM decides which to use."""
    discovered = discover_skills()

    bash_hint = "使用 Git Bash 执行命令" if IS_WINDOWS else "使用系统 bash 执行命令"
    platform_line = f"\n\n## 运行环境\n当前运行环境：{PLATFORM_HINT}，{bash_hint}。\n"

    prompt = platform_line + _BASE_PROMPT

    # 加载场景化用户画像到 system prompt
    try:
        user_profile = read_profile()
        if user_profile.strip():
            scenario_profile = _extract_scenario_section(user_profile, scenario)
            if scenario_profile:
                prompt += "\n\n## 用户音乐画像（当前场景）\n以下是该用户在当前场景下的音乐偏好画像，请参考这些偏好来推荐音乐：\n\n" + scenario_profile
    except Exception as e:
        logger.warning(f"[prompt] Failed to load user profile: {e}")

    for skill in discovered:
        _, skill_body = load_skill(skill["name"])
        if skill_body:
            prompt += "\n\n" + skill_body

    prompt += "\n" + _OUTPUT_FORMAT
    return prompt


def _extract_scenario_section(profile_text: str, scenario: str = "默认") -> str:
    """Extract the matching scenario section from user_profile.md.

    Falls back to '默认' if the specified scenario is not found.
    """
    target = scenario or "默认"
    lines = profile_text.split("\n")

    start = None
    end = None
    fallback_start = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## 场景:"):
            sname = stripped.replace("## 场景:", "").strip()
            if sname == target:
                start = i
            elif sname == "默认" and fallback_start is None:
                fallback_start = i
            elif start is not None and end is None:
                end = i

    if start is None:
        start = fallback_start
    if start is None:
        return ""

    if end is None:
        for i in range(start + 1, len(lines)):
            if lines[i].strip().startswith("## "):
                end = i
                break
        if end is None:
            end = len(lines)

    return "\n".join(lines[start:end]).strip()


def _trigger_wiki_ingest(urls: list[str], song_meta_json: str, target_dir: str) -> None:
    """Trigger wiki ingest synchronously after successful conversion."""
    import re

    def _parse_filename_meta(filename: str) -> dict:
        """Parse artist, title, bvid from filename like '歌手-歌名-BVxxx.mp3'."""
        base = filename[:-4] if filename.endswith(".mp3") else filename
        result = {}

        # Extract bvid from end
        bvid_match = re.search(r"[_ ]?(BV[A-Za-z0-9]+)$", base)
        if bvid_match:
            result["bvid"] = bvid_match.group(1)
            base = base[: -len(bvid_match.group(0))]

        # Split by dash: expect artist-title or title
        parts = base.split("-")
        if len(parts) >= 2:
            result["artist"] = parts[0].strip()
            result["title"] = "-".join(parts[1:]).strip()
        elif len(parts) == 1:
            result["title"] = parts[0].strip()

        return result

    def _run():
        try:
            from services.wiki_manager import get_wiki_status
            from services.wiki_ingest import ingest_song

            status = get_wiki_status()
            if not status.get("initialized"):
                logger.info("[wiki] Wiki not initialized, auto-initializing")
                from services.wiki_manager import init_wiki
                init_wiki()

            # Parse song metadata if provided
            meta_list = []
            if song_meta_json:
                try:
                    meta_list = json.loads(song_meta_json)
                    if not isinstance(meta_list, list):
                        meta_list = [meta_list]
                except json.JSONDecodeError:
                    pass

            # For each URL, try to find matching metadata or create minimal entry
            for url in urls:
                # Extract bvid from URL
                bvid = ""
                if "bilibili.com/video/" in url:
                    bvid = url.split("bilibili.com/video/")[-1].split("?")[0]

                # Find matching metadata
                song_meta = {}
                for m in meta_list:
                    if m.get("bvid") == bvid or m.get("url") == url:
                        song_meta = m
                        break

                if not song_meta:
                    song_meta = {"bvid": bvid, "url": url, "title": ""}

                # Apply fallback: artist→"Unknown", title→videoTitle
                if not song_meta.get("artist"):
                    song_meta["artist"] = "Unknown"
                if not song_meta.get("title"):
                    video_title = song_meta.get("videoTitle", "") or song_meta.get("video_title", "")
                    song_meta["title"] = video_title or "Unknown"

                # Try to find the local file and parse metadata from filename
                if target_dir and os.path.isdir(target_dir):
                    for f in os.listdir(target_dir):
                        if bvid and bvid in f and f.endswith(".mp3"):
                            song_meta["local_file_path"] = os.path.join(target_dir, f)
                            # Fallback: parse title/artist from filename
                            if not song_meta.get("title") or not song_meta.get("artist"):
                                filename_meta = _parse_filename_meta(f)
                                if not song_meta.get("title"):
                                    song_meta["title"] = filename_meta.get("title", "")
                                if not song_meta.get("artist"):
                                    song_meta["artist"] = filename_meta.get("artist", "")
                            break

                song_meta.setdefault("title", bvid or "")
                song_meta.setdefault("artist", "")
                song_meta.setdefault("bvid", bvid)

                try:
                    result = ingest_song(song_meta)
                    logger.info(f"[wiki] Ingest result: {result}")
                except Exception as e:
                    logger.error(f"[wiki] Ingest failed for {bvid}: {e}")

        except Exception as e:
            logger.error(f"[wiki] Trigger failed: {e}")

    _run()


# ── LangGraph Agent ─────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _build_tools(scenario: str = "默认") -> list:
    """Build LangChain tools for the agent."""

    @tool
    def bash(command: str) -> str:
        """Execute a bash command and return the output. Use this for running curl commands, ls, diff, sed, and other shell operations."""
        try:
            bash_exe = _find_bash() if IS_WINDOWS else "/bin/bash"
            # Pass MUSIC_DIR and PROJECT_ROOT so $MUSIC_DIR works in shell commands
            # On Windows, convert to Unix-style paths for Git Bash
            env = os.environ.copy()
            if IS_WINDOWS:
                env["MUSIC_DIR"] = _to_unix_path(settings.MUSIC_DIR)
                env["PROJECT_ROOT"] = _to_unix_path(str(PROJECT_ROOT))
            else:
                env["MUSIC_DIR"] = settings.MUSIC_DIR
                env["PROJECT_ROOT"] = str(PROJECT_ROOT)
            result = subprocess.run(
                [bash_exe, "--login", "-c", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                cwd=str(PROJECT_ROOT),
                env=env,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr] {result.stderr}"
            return output.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return "[error] Command timed out after 120 seconds"
        except Exception as e:
            return f"[error] {e}"

    @tool
    def bili_search(keyword: str) -> str:
        """Search Bilibili for videos by keyword. Returns JSON with total count and videos array (each with bvid, title, author, duration, play, pic)."""
        import asyncio
        import httpx
        from services.bili_client import search_videos

        async def _search():
            async with httpx.AsyncClient(timeout=30) as client:
                return await search_videos(client, keyword)

        result = asyncio.run(_search())
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    def local_search(query: str, limit: int = 20) -> str:
        """Search local music library by keyword. Returns JSON with total count and tracks array (each with id, title, author, url, filename, bvid)."""
        import asyncio
        import httpx

        async def _search():
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "http://localhost:8000/api/search",
                    params={"q": query, "limit": limit},
                )
                return resp.json()

        result = asyncio.run(_search())
        return json.dumps(result, ensure_ascii=False, default=str)

    @tool
    def convert_video(urls: list[str], song_meta_json: str = "") -> str:
        """Download and convert Bilibili videos to MP3.

        Args:
            urls: List of Bilibili video URLs (e.g., ["https://www.bilibili.com/video/BV1xxxxx"]).
            song_meta_json: Required JSON array string with metadata for each URL. Each element must contain:
                - bvid (str): BV号, required
                - title (str): 纯净歌名, required (从视频标题中解析, 去除UP主名/前缀/后缀)
                - artist (str): 纯净歌手名, required (从视频标题中解析, 不是UP主名字)
                - uploader (str): UP主名字, optional
                - videoTitle (str): 视频原始标题, optional
                Example: '[{"bvid":"BV1xxxxx","title":"没有理想的人不伤心","artist":"新裤子","uploader":"JLRS-LeoFM","videoTitle":"在百万豪装录音棚大声听 新裤子《没有理想的人不伤心》【Hi-res】"}]'

        Returns:
            JSON string with: {"success": bool, "files": [{"original", "renamed", "bvid"}], "errors": []}.
        """
        from datetime import datetime

        today = datetime.now().strftime("%Y%m%d")
        target_dir = os.path.join(settings.MUSIC_DIR, today)

        if not os.path.isdir(settings.MUSIC_DIR):
            return json.dumps({"success": False, "error": f"MUSIC_DIR does not exist: {settings.MUSIC_DIR}", "files": [], "errors": []})

        os.makedirs(target_dir, exist_ok=True)

        # Parse song metadata
        meta_list = []
        if song_meta_json:
            try:
                meta_list = json.loads(song_meta_json)
                if not isinstance(meta_list, list):
                    meta_list = [meta_list]
            except json.JSONDecodeError:
                pass

        # Build bvid -> meta mapping
        meta_by_bvid = {}
        for m in meta_list:
            bvid = m.get("bvid", "")
            if bvid:
                meta_by_bvid[bvid] = m

        # Get list of existing files before conversion
        existing_files = set(os.listdir(target_dir)) if os.path.isdir(target_dir) else set()

        url_args = " ".join(f"-u {u}" for u in urls)
        unix_dir = _to_unix_path(target_dir)
        command = f'cd "{unix_dir}" && npx bv2mp3 --threads 20 {url_args}'

        bash_exe = _find_bash() if IS_WINDOWS else "/bin/bash"
        print(f"[convert_video] target_dir={target_dir}")
        print(f"[convert_video] command={command}")

        try:
            result = subprocess.run(
                [bash_exe, "--login", "-c", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
                return json.dumps({"success": False, "error": error_msg, "files": [], "errors": [error_msg]})

            # Clean up .flv files
            for f in os.listdir(target_dir):
                if f.endswith(".flv"):
                    try:
                        os.remove(os.path.join(target_dir, f))
                    except OSError:
                        pass

            # Find new .mp3 files and rename them
            current_files = set(os.listdir(target_dir))
            new_files = current_files - existing_files
            converted_files = []

            for f in new_files:
                if not f.endswith(".mp3"):
                    continue

                original_path = os.path.join(target_dir, f)
                # Try to extract bvid from filename (bv2mp3 may include it)
                bvid = ""
                for url in urls:
                    if "bilibili.com/video/" in url:
                        bvid = url.split("bilibili.com/video/")[-1].split("?")[0]
                        break
                if not bvid:
                    import re
                    bvid_match = re.search(r"(BV[A-Za-z0-9]+)", f)
                    if bvid_match:
                        bvid = bvid_match.group(1)

                # Find matching metadata
                meta = meta_by_bvid.get(bvid, {})
                artist = meta.get("artist", "").strip() or "Unknown"
                title = meta.get("title", "").strip()
                video_title = meta.get("videoTitle", "") or meta.get("video_title", "")
                if not title:
                    title = video_title or "Unknown"

                if bvid:
                    new_name = f"{artist}-{title}-{bvid}.mp3"
                    new_path = os.path.join(target_dir, new_name)
                    try:
                        os.rename(original_path, new_path)
                        converted_files.append({"original": f, "renamed": new_name, "bvid": bvid})
                    except OSError:
                        converted_files.append({"original": f, "renamed": f, "bvid": bvid})
                else:
                    converted_files.append({"original": f, "renamed": f, "bvid": bvid or None})

            # Trigger wiki ingest (synchronous)
            _trigger_wiki_ingest(urls, song_meta_json, target_dir)

            # Rescan target_dir to get final filenames after wiki_ingest rename
            if os.path.isdir(target_dir):
                current_files = os.listdir(target_dir)
                for entry in converted_files:
                    bvid = entry.get("bvid")
                    if bvid:
                        for f in current_files:
                            if bvid in f and f.endswith(".mp3"):
                                entry["renamed"] = f
                                break

            return json.dumps({"success": True, "files": converted_files, "errors": []}, ensure_ascii=False)

        except subprocess.TimeoutExpired:
            return json.dumps({"success": False, "error": "timeout", "files": [], "errors": ["Command timed out after 120 seconds"]})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e), "files": [], "errors": [str(e)]})

    @tool
    def read_file(path: str) -> str:
        """Read the contents of a file at the given path."""
        try:
            expanded = os.path.expanduser(path)
            with open(expanded, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            return f"[error] {e}"

    @tool
    def wiki_search(query: str) -> str:
        """Search the music knowledge base (LLM-Wiki) for information about songs, artists, genres, and albums. Use this when the user asks about music knowledge, preferences, history, or wants recommendations based on past listening. Do NOT use this when the user specifies an exact song title to play."""
        # Step 1: LLM query understanding
        kw_result = _extract_query_keywords(query)
        entities = kw_result.get("entities", [query])
        intent = kw_result.get("intent", query)

        # Step 2: Resolve aliases to canonical names
        alias_index = load_alias_index()
        resolved = [resolve_name(e, alias_index) for e in entities]

        # Step 2.5: Inject profile entities for recommendation queries
        if _is_recommendation_intent(intent):
            profile_entities = _extract_profile_entities(scenario)
            for pe in profile_entities:
                resolved_name = resolve_name(pe, alias_index)
                if resolved_name not in resolved:
                    resolved.append(resolved_name)

        # Step 3: Build structured query
        enhanced_query = f"搜索关键词: {', '.join(set(resolved))}\n搜索意图: {intent}"

        # Step 4: Inject user profile summary
        profile_summary = _extract_profile_summary(scenario)
        if profile_summary:
            enhanced_query += f"\n\n[用户画像参考] {profile_summary}"

        sub_agent = _build_wiki_sub_agent()
        result = sub_agent.invoke(
            {"messages": [HumanMessage(content=enhanced_query)]},
            config={"recursion_limit": 50},
        )
        last_msg = result["messages"][-1]
        return last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    return [bash, bili_search, local_search, convert_video, read_file, wiki_search]


# ── Wiki Sub-Agent ──────────────────────────────────────────────────────────

_WIKI_SUB_AGENT_PROMPT = """你是 Musicer 的知识库检索子 Agent。你的唯一任务是搜索 LLM-Wiki 知识库并返回结果。

查询格式：搜索关键词: 关键词1, 关键词2\n搜索意图: 描述

## 检索流程（必须严格按顺序执行）

### Step 1: 在 index.md 中搜索关键词
用 grep 在索引文件中搜索关键词，获取匹配的实体名和分类：
```bash
grep -i "关键词" "{wiki_dir}/index.md"
```
如果 index.md 很大，不要 cat 整个文件，只用 grep 获取匹配行。

从匹配行推导文件路径（根据 section 和实体名）：
- `## Artists` 下的 `[[周杰伦]]` → `wiki/entities/artists/周杰伦.md`
- `## Songs` 下的 `[[晴天]]` → `wiki/entities/songs/晴天.md`
- `## Albums` 下的 `[[范特西]]` → `wiki/entities/albums/范特西.md`
- `## Genres` 下的 `[[摇滚]]` → `wiki/entities/genres/摇滚.md`

如果 index.md 无匹配，fallback 搜索文件内容：
```bash
grep -r -i -l "关键词" "{wiki_dir}/wiki/entities/"
```

### Step 2: 读取文件 + 链接遍历（1 层）
对 Step 1 中推导出的文件路径，读取内容：
```bash
cat "{wiki_dir}/wiki/entities/artists/周杰伦.md"
```
单页超过 2000 字时只读 frontmatter + 前 500 字。

**链接遍历**：读取文件时，提取其中的 `[[wikilinks]]` 链接（格式：`[[实体名]]`）。
对每个链接，根据实体类型构造路径并读取：
- [[歌手名]] → `wiki/entities/artists/{{歌手名}}.md`
- [[歌曲名]] → `wiki/entities/songs/{{歌曲名}}.md`
- [[专辑名]] → `wiki/entities/albums/{{专辑名}}.md`
- [[流派名]] → `wiki/entities/genres/{{流派名}}.md`

**只遍历 1 层**：链接遍历读取的页面中的新链接不再递归。

### Step 3: 排序规则
- 文件名精确命中 → 100 分
- index.md 中有 [[wiki链接]] → 80 分
- 正文关键词出现次数 × 10 → 最高 50 分

## 输出格式

搜索完成后，用自然语言综合回答用户的问题，引用知识库中的具体信息。
如果查询中包含 [用户画像参考]，请结合用户的偏好（音乐类型、歌手等）来筛选和排序搜索结果，优先推荐与用户画像匹配的内容。

如果知识库中没有相关内容，直接说"知识库中暂无相关信息"，不要编造。

## 重要：停止条件
- 你最多只能执行 5 次 bash 工具调用（grep + cat）
- 搜索到足够信息后立即用自然语言回答，不要继续搜索
- 如果 grep 搜索 index.md 后已找到匹配的实体，直接读取对应文件即可，不需要再做额外搜索"""


def _build_wiki_sub_agent():
    """Build a standalone LangGraph sub-agent for wiki queries."""
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool as _tool

    llm = ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        max_completion_tokens=2048,
        streaming=False,
    )

    wiki_dir = settings.WIKI_DIR

    @_tool
    def bash(command: str) -> str:
        """Execute a bash command for wiki search."""
        try:
            bash_exe = _find_bash() if IS_WINDOWS else "/bin/bash"
            result = subprocess.run(
                [bash_exe, "--login", "-c", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                cwd=wiki_dir,
            )
            return result.stdout.strip() or "(no output)"
        except Exception as e:
            return f"[error] {e}"

    tools = [bash]
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        system_msg = SystemMessage(
            content=_WIKI_SUB_AGENT_PROMPT.format(wiki_dir=wiki_dir.replace("\\", "/"))
        )
        full_messages = [system_msg] + list(messages)
        response = llm_with_tools.invoke(full_messages)
        return {"messages": [response]}

    tool_node = ToolNode(tools)

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


def _extract_query_keywords(query: str) -> dict:
    """Use LLM to extract entity keywords and search intent from user query.

    Returns {"entities": [...], "intent": "..."}.
    Falls back to raw query on failure.
    """
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            max_completion_tokens=256,
            streaming=False,
        )
        resp = llm.invoke([
            SystemMessage(content=(
                "从用户查询中提取音乐实体关键词（歌曲名、歌手名、流派名、专辑名）和搜索意图。\n"
                "返回 JSON 格式：{\"entities\": [\"关键词1\", \"关键词2\"], \"intent\": \"搜索意图描述\"}\n"
                "只返回 JSON，不要其他内容。"
            )),
            HumanMessage(content=query),
        ])
        text = resp.content.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
    except Exception as e:
        logger.warning(f"[wiki] Query keyword extraction failed: {e}")
        return {"entities": [query], "intent": query}


def _is_recommendation_intent(intent: str) -> bool:
    """Check if the intent is recommendation-related."""
    keywords = ["推荐", "建议", "推荐歌", "推荐音乐", "推荐一些", "有什么歌", "有什么音乐", "适合听", "想听"]
    return any(kw in intent for kw in keywords)


def _extract_profile_entities(scenario: str = "默认") -> List[str]:
    """Extract genre and artist names from user profile for query enrichment."""
    try:
        profile = read_profile()
        if not profile.strip():
            return []
        lines = profile.split("\n")

        target_scenario = scenario or "默认"
        scenario_start = None
        scenario_end = None
        fallback_start = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## 场景:"):
                sname = stripped.replace("## 场景:", "").strip()
                if sname == target_scenario:
                    scenario_start = i
                elif sname == "默认" and fallback_start is None:
                    fallback_start = i
                elif scenario_start is not None and scenario_end is None:
                    scenario_end = i

        if scenario_start is None:
            scenario_start = fallback_start
        if scenario_start is None:
            return []

        if scenario_end is None:
            for i in range(scenario_start + 1, len(lines)):
                if lines[i].strip().startswith("## "):
                    scenario_end = i
                    break
            if scenario_end is None:
                scenario_end = len(lines)

        entities = []
        in_types = False
        in_artists = False
        for i in range(scenario_start, scenario_end):
            stripped = lines[i].strip()
            if stripped == "### 最爱音乐类型":
                in_types = True
                in_artists = False
            elif stripped == "### 核心偏好歌手/乐队":
                in_types = False
                in_artists = True
            elif stripped.startswith("### ") or stripped.startswith("## "):
                in_types = False
                in_artists = False
            elif in_types and stripped.startswith(("1.", "2.", "3.")):
                # Extract genre name: "1. **英伦摇滚** (占比: 66.7%)" → "英伦摇滚"
                import re
                m = re.search(r"\*\*(.+?)\*\*", stripped)
                if m:
                    entities.append(m.group(1))
            elif in_artists and stripped.startswith("* "):
                # Extract artist names from line like "* **华语/亚洲:** 飞儿乐团 (F.I.R.), 彭佳慧"
                import re
                # Get text after the colon
                colon_idx = stripped.find(":")
                if colon_idx >= 0:
                    names_str = stripped[colon_idx + 1:].strip()
                    # Split by comma, paren, or Chinese comma
                    parts = re.split(r"[,，、()（）]", names_str)
                    for p in parts:
                        p = p.strip()
                        if p and p != "作曲家 E":
                            entities.append(p)
            if len(entities) >= 10:
                break

        return entities
    except Exception:
        return []


def _extract_profile_summary(scenario: str = "默认") -> str:
    """Extract a short summary from user_profile.md for wiki search context.

    Only extracts preferences from the matching scenario section.
    Falls back to '默认' if the specified scenario is not found.
    """
    try:
        profile = read_profile()
        if not profile.strip():
            return ""
        lines = profile.split("\n")

        # Find the target scenario section
        target_scenario = scenario or "默认"
        scenario_start = None
        scenario_end = None
        fallback_start = None
        fallback_end = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## 场景:"):
                sname = stripped.replace("## 场景:", "").strip()
                if sname == target_scenario:
                    scenario_start = i
                elif sname == "默认" and fallback_start is None:
                    fallback_start = i
                elif scenario_start is not None and scenario_end is None:
                    # Previous scenario ended, mark boundary
                    scenario_end = i

        # If target scenario not found, use fallback
        if scenario_start is None:
            scenario_start = fallback_start
        if scenario_start is None:
            return ""

        # Find end of scenario section (next ## or EOF)
        if scenario_end is None:
            for i in range(scenario_start + 1, len(lines)):
                if lines[i].strip().startswith("## "):
                    scenario_end = i
                    break
            if scenario_end is None:
                scenario_end = len(lines)

        # Extract from scenario section only
        summary_parts = []
        in_types = False
        in_artists = False
        for i in range(scenario_start, scenario_end):
            stripped = lines[i].strip()
            if stripped == "### 最爱音乐类型":
                in_types = True
                in_artists = False
            elif stripped == "### 核心偏好歌手/乐队":
                in_types = False
                in_artists = True
            elif stripped.startswith("### ") or stripped.startswith("## "):
                in_types = False
                in_artists = False
            elif in_types and stripped.startswith(("1.", "2.", "3.")):
                summary_parts.append(stripped)
            elif in_artists and stripped.startswith("* "):
                summary_parts.append(stripped)
            if len(summary_parts) >= 10:
                break

        return "; ".join(summary_parts) if summary_parts else ""
    except Exception:
        return ""


def _build_agent(system_prompt: str, scenario: str = "默认"):
    """Build a LangGraph React Agent with the given system prompt."""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        max_completion_tokens=4096,
        streaming=True,
    )

    tools = _build_tools(scenario)
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: AgentState) -> dict:
        """Agent node: call LLM with tools."""
        messages = state["messages"]
        full_messages = [SystemMessage(content=system_prompt)] + list(messages)
        # Debug: log available tools
        print(f"[DEBUG] Available tools: {[t.name for t in tools]}")
        response = llm_with_tools.invoke(full_messages)
        return {"messages": [response]}

    tool_node = ToolNode(tools)

    def should_continue(state: AgentState) -> str:
        """Decide whether to continue with tool calls or end."""
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


# ── Conversion Progress Detection ────────────────────────────────────────────

_CONVERSION_STEPS = {
    "mkdir": {"step": 1, "label": "准备目录"},
    "bv2mp3": {"step": 3, "label": "下载转换中（可能需要几分钟）"},
    "scan": {"step": 5, "label": "扫描曲库"},
}


def _detect_conversion_progress(command: str) -> dict | None:
    """Detect conversion step markers in bash commands."""
    cmd_lower = command.lower()
    for pattern, info in _CONVERSION_STEPS.items():
        if pattern in cmd_lower:
            return info
    return None


# ── SSE Streaming ───────────────────────────────────────────────────────────

def _maybe_trigger_dream():
    """Auto-trigger Dream if 5+ new records since last dream."""
    try:
        from services.memory_manager import get_dream_offset, read_all_history
        from services.dream_engine import run_dream
        dialogues = read_all_history()
        offset = get_dream_offset()
        new_count = len(dialogues) - offset
        if new_count >= 5:
            import threading
            def _run():
                try:
                    run_dream()
                except Exception:
                    pass
            threading.Thread(target=_run, daemon=True).start()
    except Exception:
        pass


async def chat_stream(
    message: str,
    history: list[dict[str, str]],
    scenario: str = "默认",
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream agent responses as SSE events."""
    try:
        system_prompt = _build_system_prompt(scenario)
        agent = _build_agent(system_prompt, scenario)
    except Exception as e:
        yield {"event": "error", "data": {"error": f"Agent init failed: {e}"}}
        return

    # Build initial messages from history
    messages = []
    for m in history[-16:]:
        role = m.get("role", "operator")
        content = m.get("content", "")
        if role == "operator":
            messages.append(HumanMessage(content=content))
        elif role == "agent":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=message))

    yield {"event": "status", "data": {"stage": "starting"}}

    try:
        final_text = ""
        input_state: AgentState = {"messages": messages}

        async for event in agent.astream_events(input_state, version="v2", config={"recursion_limit": 50}):
            kind = event.get("event", "")

            # Stream LLM tokens
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text = chunk.content
                    if isinstance(text, str) and text:
                        final_text += text
                        yield {
                            "event": "output",
                            "data": {
                                "type": "assistant",
                                "message": {
                                    "content": [{"type": "text", "text": text}]
                                },
                            },
                        }

            # Tool call start
            elif kind == "on_chat_model_start":
                chunk = event.get("data", {}).get("chunk")
                # Check for tool calls in the output
                if event.get("name") == "agent":
                    pass  # handled in on_tool_start

            # Tool call events
            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                yield {
                    "event": "output",
                    "data": {
                        "type": "tool_call",
                        "name": tool_name,
                        "input": tool_input,
                    },
                }

                # Detect conversion step markers and emit progress
                if tool_name == "bash":
                    cmd = tool_input.get("command", "")
                    progress = _detect_conversion_progress(cmd)
                    if progress:
                        yield {
                            "event": "output",
                            "data": {
                                "type": "progress",
                                "step": progress["step"],
                                "total": 8,
                                "label": progress["label"],
                            },
                        }

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                tool_output = event.get("data", {}).get("output", "")
                yield {
                    "event": "output",
                    "data": {
                        "type": "tool_result",
                        "name": tool_name,
                        "content": str(tool_output)[:2000],
                    },
                }

        # Emit final result
        if final_text:
            yield {
                "event": "output",
                "data": {
                    "type": "result",
                    "subtype": "success",
                    "result": final_text,
                },
            }

        # 记录对话到中期记忆
        try:
            append_history(
                role="user",
                content=message,
                summary=message[:100],
                intent="",
                scenario=scenario,
            )
            if final_text:
                append_history(
                    role="agent",
                    content=final_text,
                    summary=final_text[:100],
                    intent="",
                    scenario=scenario,
                )
            # Auto-trigger Dream if 5+ new records since last dream
            _maybe_trigger_dream()
        except Exception:
            pass  # 记录失败不影响主流程

        yield {"event": "done", "data": {"status": "completed"}}

    except Exception as e:
        yield {"event": "error", "data": {"error": str(e)}}
