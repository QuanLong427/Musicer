import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.skill_loader import discover_skills, load_skill, select_skill_for_task


def test_discover_skills():
    """Test skill discovery finds all skills."""
    skills = discover_skills()
    names = [s["name"] for s in skills]
    assert "local-search" in names
    assert "cloud-search" in names
    assert "convert" in names


def test_discover_skills_metadata():
    """Test discovered skills have name and description."""
    skills = discover_skills()
    for skill in skills:
        assert "name" in skill
        assert "description" in skill
        assert len(skill["name"]) > 0
        assert len(skill["description"]) > 0


def test_select_local_search():
    """Test local search selected for local keywords."""
    skills = discover_skills()
    assert select_skill_for_task("播放晴天", skills) == "local-search"
    assert select_skill_for_task("本地曲库有什么", skills) == "local-search"


def test_select_cloud_search():
    """Test cloud search selected for cloud keywords."""
    skills = discover_skills()
    assert select_skill_for_task("去B站搜周杰伦", skills) == "cloud-search"
    assert select_skill_for_task("云端搜索晴天", skills) == "cloud-search"
    assert select_skill_for_task("网上搜一下", skills) == "cloud-search"


def test_select_convert():
    """Test convert selected for conversion keywords."""
    skills = discover_skills()
    assert select_skill_for_task("转换这个视频", skills) == "convert"
    assert select_skill_for_task("下载并转为mp3", skills) == "convert"


def test_select_default():
    """Test default selection is local-search."""
    skills = discover_skills()
    assert select_skill_for_task("你好", skills) == "local-search"
    assert select_skill_for_task("", skills) == "local-search"


def test_load_skill_local():
    """Test loading local-search skill."""
    full, body = load_skill("local-search")
    assert len(full) > 0
    assert len(body) > 0
    assert "name: local-search" in full
    assert "curl" in body


def test_load_skill_cloud():
    """Test loading cloud-search skill."""
    full, body = load_skill("cloud-search")
    assert len(full) > 0
    assert len(body) > 0
    assert "name: cloud-search" in full
    assert "bilibili" in body.lower() or "B站" in body


def test_load_skill_not_found():
    """Test loading non-existent skill returns empty."""
    full, body = load_skill("nonexistent")
    assert full == ""
    assert body == ""
