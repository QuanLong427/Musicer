"""
Memory Manager - 分层记忆管理模块

中期记忆: history.jsonl (JSONL格式，首行metadata存储dream_offset)
长期记忆: user_profile.md (结构化用户画像)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config import PROJECT_ROOT

# 路径常量
MEMORY_DIR = PROJECT_ROOT / "memory"
TEMPLATE_DIR = MEMORY_DIR / "template"
DATA_DIR = MEMORY_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.jsonl"
PROFILE_FILE = DATA_DIR / "user_profile.md"
TEMPLATE_PROFILE = TEMPLATE_DIR / "user_profile.md"

MAX_HISTORY_ENTRIES = 50  # FIFO 容量


def _ensure_dirs():
    """确保目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_history_file():
    """确保 history.jsonl 存在，不存在则初始化"""
    _ensure_dirs()
    if not HISTORY_FILE.exists():
        metadata = {
            "type": "metadata",
            "dream_offset": 0,
            "created_at": datetime.now().isoformat(),
        }
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(metadata, ensure_ascii=False) + "\n")


def _read_all_lines() -> List[Dict[str, Any]]:
    """读取 history.jsonl 所有行"""
    _ensure_history_file()
    lines = []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


def _write_all_lines(lines: List[Dict[str, Any]]):
    """写入所有行到 history.jsonl"""
    _ensure_dirs()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ── 长期记忆 (Profile) ──────────────────────────────────────────────────────


def read_profile() -> str:
    """读取长期记忆 user_profile.md"""
    _ensure_dirs()
    if not PROFILE_FILE.exists():
        # 从模板复制
        if TEMPLATE_PROFILE.exists():
            return TEMPLATE_PROFILE.read_text(encoding="utf-8")
        return ""
    return PROFILE_FILE.read_text(encoding="utf-8")


def write_profile(content: str):
    """写入长期记忆 user_profile.md"""
    _ensure_dirs()
    PROFILE_FILE.write_text(content, encoding="utf-8")


# ── 中期记忆 (History) ──────────────────────────────────────────────────────


def init_history_file():
    """初始化 history.jsonl（创建 metadata 行）"""
    _ensure_history_file()


def append_history(
    role: str,
    content: str,
    summary: str = "",
    intent: str = "",
    scenario: str = "默认",
):
    """
    追加一条对话记录到 history.jsonl

    Args:
        role: 角色 (user/agent)
        content: 消息内容
        summary: 消息摘要
        intent: 意图标签
        scenario: 场景标签
    """
    _ensure_history_file()
    lines = _read_all_lines()

    # 构造新记录
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content,
        "summary": summary,
        "intent": intent,
        "scenario": scenario,
    }

    # 分离 metadata 和对话记录
    metadata = lines[0] if lines and lines[0].get("type") == "metadata" else {
        "type": "metadata",
        "dream_offset": 0,
        "created_at": datetime.now().isoformat(),
    }
    dialogues = [l for l in lines if l.get("type") != "metadata"]

    # 追加新记录
    dialogues.append(entry)

    # FIFO: 保留最近 N 条
    if len(dialogues) > MAX_HISTORY_ENTRIES:
        overflow = len(dialogues) - MAX_HISTORY_ENTRIES
        dialogues = dialogues[overflow:]
        # 如果删除了已处理的记录，需要调整 offset
        metadata["dream_offset"] = max(0, metadata["dream_offset"] - overflow)

    # 重写文件
    _write_all_lines([metadata] + dialogues)


def read_all_history() -> List[Dict[str, Any]]:
    """读取所有对话记录（不含 metadata）"""
    lines = _read_all_lines()
    return [l for l in lines if l.get("type") != "metadata"]


def read_history_from_offset() -> List[Dict[str, Any]]:
    """从 dream_offset 读取新的对话记录"""
    lines = _read_all_lines()
    metadata = lines[0] if lines and lines[0].get("type") == "metadata" else {"dream_offset": 0}
    dialogues = [l for l in lines if l.get("type") != "metadata"]
    offset = metadata.get("dream_offset", 0)
    return dialogues[offset:]


def get_dream_offset() -> int:
    """获取当前 dream_offset"""
    lines = _read_all_lines()
    if lines and lines[0].get("type") == "metadata":
        return lines[0].get("dream_offset", 0)
    return 0


def update_dream_offset(new_offset: int):
    """更新 dream_offset"""
    _ensure_history_file()
    lines = _read_all_lines()
    if lines and lines[0].get("type") == "metadata":
        lines[0]["dream_offset"] = new_offset
        _write_all_lines(lines)
