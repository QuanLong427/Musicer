import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from services.wiki_manager import init_wiki, get_wiki_status
from services.wiki_ingest import ingest_song

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


class IngestRequest(BaseModel):
    title: str
    artist: str = ""
    bvid: str = ""
    local_file_path: str = ""
    album: str = ""
    genre: str = ""
    description: str = ""
    duration: int = 0
    url: str = ""


@router.post("/init")
async def wiki_init():
    """Initialize the wiki directory structure."""
    result = init_wiki()
    return result


@router.get("/status")
async def wiki_status():
    """Get wiki initialization status and statistics."""
    return get_wiki_status()


@router.post("/ingest")
async def wiki_ingest(req: IngestRequest):
    """Ingest a song into the wiki. Runs asynchronously."""
    wiki_dir = settings.WIKI_DIR

    # Check if wiki is initialized
    status = get_wiki_status(wiki_dir)
    if not status.get("initialized"):
        raise HTTPException(status_code=400, detail="Wiki not initialized. Call POST /api/wiki/init first.")

    song_meta = req.model_dump()

    # Run ingest in background to not block the response
    async def _run_ingest():
        try:
            await asyncio.to_thread(ingest_song, song_meta, wiki_dir)
            logger.info(f"Wiki ingest completed for: {req.title}")
        except Exception as e:
            logger.error(f"Wiki ingest failed for {req.title}: {e}")

    asyncio.create_task(_run_ingest())

    return {"status": "ingest_started", "title": req.title}
