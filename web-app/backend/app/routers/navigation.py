from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.robot import NavigationStartRequest, NavigationRequestOut
from app.schemas.tour import NarrationOut
from app.services.navigation_service import NavigationService
from app.services.tour_service import _build_narration
from app.services.voice_service import text_to_speech_base64
from app.models.exhibit import Exhibit
from app.models.robot import NavigationRequest

router = APIRouter()


@router.post("/start", response_model=NavigationRequestOut)
def start_navigation(
    payload: NavigationStartRequest,
    language: str = Query("en", pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    try:
        return NavigationService.start(db, payload.exhibit_id, language)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("/stop")
def stop_navigation(db: Session = Depends(get_db)):
    return NavigationService.stop(db)


@router.get("/status", response_model=NavigationRequestOut | None)
def navigation_status(db: Session = Depends(get_db)):
    return NavigationService.current_status(db)


@router.get("/state")
def navigation_state(
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    """Rich state for the ExhibitDetailPage's inline navigation panel."""
    return NavigationService.status(db, language=lang)


@router.get("/narration", response_model=NarrationOut | None)
def navigation_narration(
    request_id: int,
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    with_audio: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Narration for a single-exhibit (non-tour) arrival — same language
    handling as tour narration."""
    nav = db.query(NavigationRequest).filter(NavigationRequest.id == request_id).first()
    if not nav or nav.status != "arrived":
        return None
    exhibit = db.query(Exhibit).filter(Exhibit.id == nav.target_exhibit_id).first()
    if not exhibit:
        return None
    narration = _build_narration(exhibit, lang, has_more_stops=False)
    audio_b64 = None
    if with_audio:
        try:
            audio_b64 = text_to_speech_base64(narration, lang)
        except Exception as e:
            print(f"[nav] TTS failed: {e}")
    return NarrationOut(
        exhibit_id=exhibit.id,
        exhibit_title=getattr(exhibit, f"title_{lang}", None) or exhibit.title_en,
        narration=narration,
        has_more_stops=False,
        language=lang,
        audio_base64=audio_b64,
    )
