"""FastAPI layer for DUNE: Imperium Uprising web UI."""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .game_session import GameSession

app = FastAPI(title="DUNE: Imperium Uprising")

_session: Optional[GameSession] = None

STATIC_DIR = Path(__file__).parent / "static"


# ─────────────────── request models ───────────────────

class NewGameRequest(BaseModel):
    player_count: int = 3
    human_name: str = "Player"


class ActionRequest(BaseModel):
    type: str
    card_id: Optional[str] = None
    location_id: Optional[str] = None
    troops: Optional[int] = 0
    source: Optional[str] = "row"
    contract_id: Optional[str] = None
    option_id: Optional[str] = None


# ─────────────────── endpoints ────────────────────────

@app.post("/api/new-game")
def new_game(req: NewGameRequest):
    global _session
    try:
        _session = GameSession.new(
            player_count=req.player_count,
            human_name=req.human_name,
        )
        return _session.snapshot()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/state")
def get_state():
    if _session is None:
        raise HTTPException(status_code=404, detail="No active game — POST /api/new-game first")
    return _session.snapshot()


@app.post("/api/action")
def execute_action(req: ActionRequest):
    if _session is None:
        raise HTTPException(status_code=404, detail="No active game")
    result = _session.execute_action(req.model_dump(exclude_none=False))
    if "error" in result and "state" not in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/leaders")
def list_leaders():
    """Return available leaders for a new-game setup screen."""
    from src.loaders.card_loader import load_leaders
    leaders = load_leaders()
    return [{"id": int(l.id), "name": l.name} for l in leaders]


# ─────────────────── static / SPA ─────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
