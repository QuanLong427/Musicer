import json
import os
import shutil
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import PROJECT_ROOT
from services.ai_agent import chat_stream
from services.memory_manager import (
    get_clear_offset,
    read_all_history,
    reset_memory,
    update_clear_offset,
)

router = APIRouter(tags=["chat"])


def _sse_response(result_text: str) -> StreamingResponse:
    """Build an SSE response with a single result event."""
    async def event():
        yield f"event: {json.dumps({'event': 'output', 'data': {'type': 'result', 'subtype': 'success', 'result': result_text}}, ensure_ascii=False)}\n\n"
        yield f"event: done\ndata: {json.dumps({'status': 'completed'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


class ChatRequest(BaseModel):
    message: str
    mode: str = "local"
    history: list[dict[str, str]] | None = None
    scenario: str = "默认"


@router.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    msg = req.message.strip()

    # Hardcoded slash commands — no LLM needed
    if msg == "/clear":
        dialogues = read_all_history()
        update_clear_offset(len(dialogues))
        return _sse_response("屏幕已清空")

    if msg == "/reset-wiki":
        wiki_dir = os.path.join(PROJECT_ROOT, "LLM-Wiki")
        try:
            if os.path.exists(wiki_dir):
                shutil.rmtree(wiki_dir)
            from services.wiki_manager import init_wiki
            init_wiki()
            return _sse_response("LLM-Wiki 已重置并重新初始化完成")
        except Exception as e:
            return _sse_response(f"重置失败: {e}")

    if msg == "/reset-memory":
        try:
            reset_memory()
            return _sse_response("用户记忆已重置完成")
        except Exception as e:
            return _sse_response(f"重置记忆失败: {e}")

    async def event_generator():
        async for event in chat_stream(
            message=msg,
            history=req.history or [],
            scenario=req.scenario,
        ):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
