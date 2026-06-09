from fastapi import APIRouter
from services.memory_manager import get_clear_offset, read_all_history

router = APIRouter(tags=["history"])


@router.get("/api/history")
async def get_history():
    """获取所有历史会话记录"""
    records = read_all_history()
    clear_offset = get_clear_offset()
    return {"history": records, "clear_offset": clear_offset}
