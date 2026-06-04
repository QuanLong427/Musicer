import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.ai_agent import chat_stream

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    mode: str = "local"
    history: list[dict[str, str]] | None = None
    scenario: str = "默认"


@router.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    async def event_generator():
        async for event in chat_stream(
            message=req.message,
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
