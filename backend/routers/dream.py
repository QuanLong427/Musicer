from fastapi import APIRouter
from services.dream_engine import run_dream

router = APIRouter(tags=["dream"])


@router.post("/api/dream")
async def trigger_dream():
    """手动触发 Dream 引擎，从对话历史总结用户画像"""
    result = run_dream()
    return result
