"""
Scenario Manager - 场景管理模块

管理用户自定义场景，存储到 db/scenario.yml
"""

from pathlib import Path
from typing import List

import yaml

from config import PROJECT_ROOT

SCENARIO_FILE = PROJECT_ROOT / "db" / "scenario.yml"


def _ensure_file():
    """确保 scenario.yml 存在"""
    SCENARIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SCENARIO_FILE.exists():
        default = {"scenarios": ["默认", "编程", "跑步", "睡觉", "驾驶"]}
        with open(SCENARIO_FILE, "w", encoding="utf-8") as f:
            yaml.dump(default, f, allow_unicode=True, default_flow_style=False)


def read_scenarios() -> List[str]:
    """读取场景列表"""
    _ensure_file()
    with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("scenarios", ["默认"])


def write_scenarios(scenarios: List[str]):
    """写入场景列表"""
    _ensure_file()
    data = {"scenarios": scenarios}
    with open(SCENARIO_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def add_scenario(name: str) -> List[str]:
    """添加新场景，返回更新后的列表"""
    scenarios = read_scenarios()
    if name not in scenarios:
        scenarios.append(name)
        write_scenarios(scenarios)
    return scenarios


def remove_scenario(name: str) -> List[str]:
    """删除场景，返回更新后的列表"""
    scenarios = read_scenarios()
    if name in scenarios:
        scenarios.remove(name)
        write_scenarios(scenarios)
    return scenarios
