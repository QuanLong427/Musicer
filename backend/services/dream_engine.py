"""
Dream Engine - 从对话历史中总结用户画像

定期调用 LLM，将 history.jsonl 中的新记录总结到 user_profile.md
按场景分组分析偏好
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from openai import OpenAI

from config import settings
from services.memory_manager import (
    get_dream_offset,
    read_history_from_offset,
    read_profile,
    update_dream_offset,
    write_profile,
)
from services.scenario_manager import read_scenarios

logger = logging.getLogger(__name__)

# Dream 系统提示词
DREAM_SYSTEM_PROMPT = """你是一个音乐偏好分析引擎。你的任务是根据用户的对话历史，更新用户的音乐画像。

规则：
1. 只更新有新数据的部分，不要重复已有的偏好
2. 保留原有的偏好，只添加新的发现
3. 按场景分组分析偏好（每个场景独立维护：音乐类型偏好占比、核心歌手/乐队、近期听歌轨迹）
4. 更新"近期听歌轨迹"表格（FIFO，保留最近20首）
5. 如果发现新的核心歌手/乐队，添加到对应场景
6. 如果发现新的音乐类型偏好，更新占比
7. 不同场景的偏好互不影响，各自独立

输出格式：直接输出更新后的完整 user_profile.md 内容，保持原有格式。"""


def _group_by_scenario(records: List[Dict[str, Any]]) -> dict[str, List[Dict[str, Any]]]:
    """按场景分组对话记录"""
    grouped: dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        scenario = r.get("scenario", "默认") or "默认"
        grouped[scenario].append(r)
    return dict(grouped)


def _build_dream_prompt(
    new_records: List[Dict[str, Any]],
    current_profile: str,
    scenarios: List[str],
) -> str:
    """构建 Dream 提示词，按场景分组展示"""
    grouped = _group_by_scenario(new_records)

    sections = []
    for scenario, records in sorted(grouped.items()):
        records_text = "\n".join(
            f"  [{r.get('timestamp', '')}] {r.get('role', '')}: {r.get('content', '')}"
            for r in records
        )
        sections.append(f"【场景: {scenario}】({len(records)} 条)\n{records_text}")

    records_text = "\n\n".join(sections)
    scenarios_text = ", ".join(scenarios)

    return f"""以下是用户的新对话历史（已按场景分组）：

{records_text}

当前用户画像：
{current_profile}

当前所有场景列表：{scenarios_text}

请根据新的对话历史，更新用户画像。注意：
1. 保留原有偏好，只添加新发现
2. 按场景分组更新——不同场景的偏好独立维护
3. 确保用户画像中包含以上所有场景的 section，如果某个场景在画像中没有对应 section，请创建一个空的模板 section
4. 每个场景内更新：音乐类型偏好占比、核心歌手/乐队、近期听歌轨迹
5. 更新近期听歌轨迹（如果对话中提到了具体的歌曲）
6. 不要混淆不同场景的偏好"""


def _validate_dream_output(profile_text: str) -> bool:
    """Validate that LLM output contains required sections."""
    required = ["## 全局基准", "## 场景:"]
    for section in required:
        if section not in profile_text:
            logger.warning(f"[dream] Missing required section in output: {section}")
            return False
    return True


def run_dream() -> dict[str, Any]:
    """
    执行 Dream：从 history.jsonl 总结用户画像到 user_profile.md

    Returns:
        {
            "status": "success" | "no_new_data" | "error",
            "processed_count": int,
            "message": str,
        }
    """
    # 1. 读取新记录
    new_records = read_history_from_offset()
    if not new_records:
        return {
            "status": "no_new_data",
            "processed_count": 0,
            "message": "没有新的对话记录需要处理",
        }

    # 2. 读取当前画像
    current_profile = read_profile()

    # 3. 读取场景列表
    scenarios = read_scenarios()

    # 4. 按场景分组统计
    grouped = _group_by_scenario(new_records)
    scenario_summary = ", ".join(f"{s}({len(r)}条)" for s, r in sorted(grouped.items()))

    # 5. 调用 LLM 总结
    try:
        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

        response = client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[
                {"role": "system", "content": DREAM_SYSTEM_PROMPT},
                {"role": "user", "content": _build_dream_prompt(new_records, current_profile, scenarios)},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        updated_profile = response.choices[0].message.content

        # 5. Validate output
        if not _validate_dream_output(updated_profile):
            logger.warning("[dream] LLM output failed validation, skipping profile write")
            return {
                "status": "error",
                "processed_count": 0,
                "message": "LLM output missing required sections (## 全局基准, ## 场景:)",
            }

        # 6. 写入更新后的画像
        # 添加更新时间戳
        timestamp_line = f"> **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (由 Dream 引擎自动更新)\n"
        if "> **Last Updated:**" in updated_profile:
            # 替换已有的时间戳
            lines = updated_profile.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("> **Last Updated:**"):
                    lines[i] = timestamp_line.strip()
                    break
            updated_profile = "\n".join(lines)
        else:
            # 在文件开头添加时间戳
            updated_profile = timestamp_line + updated_profile

        write_profile(updated_profile)

        # 7. 更新 dream_offset
        current_offset = get_dream_offset()
        new_offset = current_offset + len(new_records)
        update_dream_offset(new_offset)

        return {
            "status": "success",
            "processed_count": len(new_records),
            "message": f"成功处理 {len(new_records)} 条对话记录（{scenario_summary}），用户画像已更新",
        }

    except Exception as e:
        return {
            "status": "error",
            "processed_count": 0,
            "message": f"Dream 失败: {str(e)}",
        }
