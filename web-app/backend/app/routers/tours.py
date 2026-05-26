from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.exhibit import Exhibit
from app.models.tour import Tour, TourStop
from app.schemas.tour import (
    NarrationOut, StartTourRequest, TourDetail, TourRunOut, TourStopOut, TourSummary,
)
from app.services.tour_service import TourService


router = APIRouter()


# ── Helpers to localize ────────────────────────────────────────────────


def _t_summary(tour: Tour, lang: str) -> TourSummary:
    return TourSummary(
        id=tour.id,
        name=getattr(tour, f"name_{lang}", None) or tour.name_en,
        description=getattr(tour, f"description_{lang}", None) or tour.description_en,
        estimated_minutes=tour.estimated_minutes,
        is_preset=tour.is_preset,
        stop_count=len(tour.stops),
        language=lang,
    )


def _stop_out(stop: TourStop, db: Session, lang: str) -> TourStopOut:
    exhibit = db.query(Exhibit).filter(Exhibit.id == stop.exhibit_id).first()
    return TourStopOut(
        sequence_order=stop.sequence_order,
        exhibit_id=stop.exhibit_id,
        exhibit_title=(getattr(exhibit, f"title_{lang}", None) or exhibit.title_en) if exhibit else "—",
        exhibit_image=exhibit.image_url if exhibit else None,
        x_position=float(exhibit.x_position) if exhibit and exhibit.x_position is not None else None,
        y_position=float(exhibit.y_position) if exhibit and exhibit.y_position is not None else None,
    )


def _run_out(run, db: Session) -> TourRunOut:
    tour = db.query(Tour).filter(Tour.id == run.tour_id).first()
    stops = sorted(tour.stops, key=lambda s: s.sequence_order) if tour else []
    lang = run.language

    cur = stops[run.current_stop_index] if 0 <= run.current_stop_index < len(stops) else None
    nxt = stops[run.current_stop_index + 1] if 0 <= run.current_stop_index + 1 < len(stops) else None

    cur_exhibit = db.query(Exhibit).filter(Exhibit.id == cur.exhibit_id).first() if cur else None
    nxt_exhibit = db.query(Exhibit).filter(Exhibit.id == nxt.exhibit_id).first() if nxt else None

    return TourRunOut(
        id=run.id,
        tour_id=run.tour_id,
        tour_name=(getattr(tour, f"name_{lang}", None) or tour.name_en) if tour else "—",
        current_stop_index=run.current_stop_index,
        total_stops=len(stops),
        status=run.status,
        language=lang,
        current_exhibit_id=cur_exhibit.id if cur_exhibit else None,
        current_exhibit_title=(getattr(cur_exhibit, f"title_{lang}", None) or cur_exhibit.title_en) if cur_exhibit else None,
        current_exhibit_image=cur_exhibit.image_url if cur_exhibit else None,
        target_x=float(cur_exhibit.x_position) if cur_exhibit and cur_exhibit.x_position is not None else None,
        target_y=float(cur_exhibit.y_position) if cur_exhibit and cur_exhibit.y_position is not None else None,
        next_exhibit_id=nxt_exhibit.id if nxt_exhibit else None,
        next_exhibit_title=(getattr(nxt_exhibit, f"title_{lang}", None) or nxt_exhibit.title_en) if nxt_exhibit else None,
        # Include every stop so the map page can render the whole route
        all_stops=[_stop_out(s, db, lang) for s in stops],
        started_at=run.started_at,
        ended_at=run.ended_at,
    )


# ── Endpoints ──────────────────────────────────────────────────────────


@router.get("/presets", response_model=list[TourSummary])
def list_presets(
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    return [_t_summary(t, lang) for t in TourService.list_presets(db)]


@router.get("/{tour_id}", response_model=TourDetail)
def get_tour(
    tour_id: int,
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    tour = TourService.get_tour(db, tour_id)
    if not tour:
        raise HTTPException(404, "Tour not found")
    summary = _t_summary(tour, lang)
    stops = [_stop_out(s, db, lang) for s in sorted(tour.stops, key=lambda s: s.sequence_order)]
    return TourDetail(**summary.model_dump(), stops=stops)


@router.post("/start", response_model=TourRunOut)
def start_tour(payload: StartTourRequest, db: Session = Depends(get_db)):
    if payload.exhibit_ids:
        tour = TourService.build_custom_tour(db, payload.exhibit_ids)
        run = TourService.start_run(db, tour.id, payload.language)
    elif payload.tour_id:
        run = TourService.start_run(db, payload.tour_id, payload.language)
    else:
        raise HTTPException(400, "Provide either tour_id or exhibit_ids")
    return _run_out(run, db)


@router.get("/runs/current", response_model=TourRunOut | None)
def current_run(db: Session = Depends(get_db)):
    run = TourService.get_active_run(db)
    if not run:
        return None
    return _run_out(run, db)


@router.post("/runs/{run_id}/next", response_model=TourRunOut)
def advance_to_next(run_id: int, db: Session = Depends(get_db)):
    run = TourService.advance(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return _run_out(run, db)


@router.get("/runs/{run_id}/narration", response_model=NarrationOut | None)
def get_narration(
    run_id: int,
    with_audio: bool = Query(True),
    lang: str | None = Query(None, pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    """Get the narration text + TTS audio for the exhibit the robot is
    currently parked at. Returns null until status == 'arrived'.

    `lang` overrides the tour's stored language so the visitor can replay
    the same narration in a different language without changing the tour.
    """
    return TourService.get_narration(db, run_id, with_audio=with_audio, lang_override=lang)


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: int, db: Session = Depends(get_db)):
    return TourService.cancel_run(db, run_id)
