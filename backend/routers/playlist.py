import logging

from fastapi import APIRouter
from pydantic import BaseModel

from services.playlist_store import get_playlist, set_playlist

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/playlist", tags=["playlist"])


class PlaylistRequest(BaseModel):
    tracks: list[dict]


@router.get("")
async def read_playlist():
    """Return the full playlist ordered by position."""
    return {"tracks": get_playlist()}


@router.post("")
async def write_playlist(req: PlaylistRequest):
    """Replace the entire playlist."""
    set_playlist(req.tracks)
    return {"status": "ok", "count": len(req.tracks)}
