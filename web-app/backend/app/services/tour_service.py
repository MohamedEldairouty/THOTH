"""
Tour orchestration service.

State machine for a TourRun:
    [start_tour]      → status = "moving",  send goal for stops[0]
    [robot arrives]   → status = "arrived"  (detected from ros_service)
    [advance]         → if more stops: status = "moving", send next goal
                         else:         status = "completed"
    [cancel]          → status = "cancelled", cancel ROS goal

No mid-route stopping. While status == "moving", advance() and detail
endpoints just return the current state; cancel() is the only escape.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.exhibit import Exhibit
from app.models.tour import Tour, TourStop, TourRun
from app.services import ros_service


# ── Helpers ────────────────────────────────────────────────────────────


def _stops_for(db: Session, tour_id: int) -> list[TourStop]:
    return (
        db.query(TourStop)
        .filter(TourStop.tour_id == tour_id)
        .order_by(TourStop.sequence_order)
        .all()
    )


def _exhibit(db: Session, exhibit_id: int) -> Exhibit | None:
    return db.query(Exhibit).filter(Exhibit.id == exhibit_id).first()


def _sync_status_with_ros(run: TourRun) -> TourRun:
    """If the ROS layer says 'completed' and we're still 'moving',
    flip to 'arrived' so the frontend can show the Continue button.
    This is the only place the moving→arrived transition happens."""
    if run.status == "moving" and ros_service.get_status() == "completed":
        run.status = "arrived"
    return run


# ── Service API ────────────────────────────────────────────────────────


class TourService:

    # ── PRESET / CUSTOM TOUR LIST ─────────────────────────────────────

    @staticmethod
    def list_presets(db: Session) -> list[Tour]:
        return (
            db.query(Tour)
            .filter(Tour.is_preset.is_(True))
            .order_by(Tour.id)
            .all()
        )

    @staticmethod
    def get_tour(db: Session, tour_id: int) -> Tour | None:
        return db.query(Tour).filter(Tour.id == tour_id).first()

    # ── CREATE A CUSTOM ONE-OFF TOUR ──────────────────────────────────

    @staticmethod
    def build_custom_tour(db: Session, exhibit_ids: list[int]) -> Tour:
        tour = Tour(
            name_en="Custom Tour",
            name_ar="جولة مخصصة",
            name_fr="Visite personnalisée",
            description_en="A custom tour built by the visitor.",
            description_ar="جولة مخصصة من اختيار الزائر.",
            description_fr="Une visite personnalisée choisie par le visiteur.",
            is_preset=False,
            estimated_minutes=max(5, len(exhibit_ids) * 4),
        )
        db.add(tour)
        db.flush()  # gets tour.id

        for i, exhibit_id in enumerate(exhibit_ids):
            db.add(TourStop(
                tour_id=tour.id,
                exhibit_id=exhibit_id,
                sequence_order=i,
            ))
        db.commit()
        db.refresh(tour)
        return tour

    # ── START / RUN A TOUR ────────────────────────────────────────────

    @staticmethod
    def get_active_run(db: Session) -> TourRun | None:
        run = (
            db.query(TourRun)
            .filter(TourRun.status.in_(["pending", "moving", "arrived"]))
            .order_by(TourRun.started_at.desc())
            .first()
        )
        if run:
            _sync_status_with_ros(run)
            db.commit()
        return run

    @staticmethod
    def start_run(db: Session, tour_id: int, language: str = "en") -> TourRun:
        # Cancel any active run first
        existing = TourService.get_active_run(db)
        if existing:
            TourService.cancel_run(db, existing.id)

        stops = _stops_for(db, tour_id)
        if not stops:
            raise ValueError(f"Tour {tour_id} has no stops")

        run = TourRun(
            tour_id=tour_id,
            current_stop_index=0,
            status="moving",
            language=language,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        first_exhibit = _exhibit(db, stops[0].exhibit_id)
        if first_exhibit and first_exhibit.x_position is not None:
            ros_service.send_goal(
                float(first_exhibit.x_position),
                float(first_exhibit.y_position),
            )
        return run

    @staticmethod
    def advance(db: Session, run_id: int) -> TourRun | None:
        run = db.query(TourRun).filter(TourRun.id == run_id).first()
        if not run:
            return None
        _sync_status_with_ros(run)

        if run.status != "arrived":
            return run   # ignore advance if robot is still moving

        stops = _stops_for(db, run.tour_id)
        next_index = run.current_stop_index + 1

        if next_index >= len(stops):
            run.status = "completed"
            run.ended_at = datetime.utcnow()
            db.commit()
            return run

        run.current_stop_index = next_index
        run.status = "moving"
        db.commit()

        next_exhibit = _exhibit(db, stops[next_index].exhibit_id)
        if next_exhibit and next_exhibit.x_position is not None:
            ros_service.send_goal(
                float(next_exhibit.x_position),
                float(next_exhibit.y_position),
            )
        return run

    @staticmethod
    def cancel_run(db: Session, run_id: int) -> dict:
        run = db.query(TourRun).filter(TourRun.id == run_id).first()
        if not run:
            return {"ok": False, "msg": "not found"}
        run.status = "cancelled"
        run.ended_at = datetime.utcnow()
        db.commit()
        ros_service.cancel_goal()
        return {"ok": True}
