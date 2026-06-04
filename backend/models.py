from pydantic import BaseModel


class Track(BaseModel):
    id: str
    title: str
    author: str
    date: str
    filename: str
    subDir: str
    size: int
    url: str
    bvid: str | None = None


class ChatMessage(BaseModel):
    id: str
    role: str  # "agent" | "operator" | "system" | "tool"
    content: str
    timestamp: int
    toolName: str | None = None


class BiliVideo(BaseModel):
    bvid: str
    title: str
    author: str
    duration: str
    play: int
    pic: str


class DanmakuItem(BaseModel):
    time: float
    content: str
    type: int
    color: str
