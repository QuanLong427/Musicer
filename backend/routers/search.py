from fastapi import APIRouter, Query

from services.music_manager import search_tracks

router = APIRouter(tags=["search"])


@router.get("/api/search")
async def search(
    q: str = Query(""),
    limit: int = Query(20, ge=1),
):
    tracks = search_tracks(q.strip(), limit)
    return {"total": len(tracks), "tracks": tracks}
