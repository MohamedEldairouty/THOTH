"""
Single-exhibit navigation (NOT a tour).

Mirrors the tour-arrival narration so the visitor gets the same
"standing in front of X" + TTS audio + Q&A prompt, but for a one-off
exhibit they tapped "Navigate Here" on from the detail page.

The frontend should NOT call this while a tour is active — the
`is_blocked_by_tour()` helper lets it disable the button.
"""
from sqlalchemy.orm import Session

from app.models.exhibit import Exhibit
from app.models.robot import NavigationRequest, RobotStatus
from app.models.tour import TourRun
from app.services import ros_service
from app.services.tour_service import _build_narration
from app.services.voice_service import text_to_speech_base64


class NavigationService:

    # ── Tour-aware gate ──────────────────────────────────────────────────
    @staticmethod
    def is_blocked_by_tour(db: Session) -> bool:
        """True if a tour is currently active (moving/arrived) — single-
        exhibit navigation should be disabled in that case."""
        active = (db.query(TourRun)
                    .filter(TourRun.status.in_(["pending", "moving", "arrived"]))
                    .first())
        return active is not None

    # ── Start a one-off goal ─────────────────────────────────────────────
    @staticmethod
    def start(db: Session, exhibit_id: int, language: str = "en") -> NavigationRequest:
        if NavigationService.is_blocked_by_tour(db):
            raise ValueError("A tour is currently active — finish or cancel it first.")

        # Cancel any in-progress single-nav requests
        db.query(NavigationRequest).filter(
            NavigationRequest.status == "in_progress"
        ).update({"status": "cancelled"})

        exhibit = db.query(Exhibit).filter(Exhibit.id == exhibit_id).first()
        target_x = float(exhibit.x_position) if exhibit and exhibit.x_position is not None else None
        target_y = float(exhibit.y_position) if exhibit and exhibit.y_position is not None else None

        nav = NavigationRequest(
            target_exhibit_id=exhibit_id,
            status="in_progress",
            estimated_time=30,
        )
        db.add(nav)

        robot = db.query(RobotStatus).first()
        if robot:
            robot.status = "navigating"

        db.commit()
        db.refresh(nav)

        if target_x is not None and target_y is not None:
            ros_service.send_goal(target_x, target_y)
        return nav

    # ── Status (single nav, not tour) ────────────────────────────────────
    @staticmethod
    def status(db: Session, language: str = "en") -> dict:
        """Combined view used by the ExhibitDetailPage to render the
        in-page navigation experience."""
        nav = (db.query(NavigationRequest)
                 .filter(NavigationRequest.status == "in_progress")
                 .order_by(NavigationRequest.created_at.desc())
                 .first())
        if not nav:
            return {"active": False, "blocked_by_tour": NavigationService.is_blocked_by_tour(db)}

        exhibit = db.query(Exhibit).filter(Exhibit.id == nav.target_exhibit_id).first()
        robot_state = ros_service.get_status()

        # Move into "arrived" once ROS says completed
        if robot_state == "completed" and nav.status == "in_progress":
            nav.status = "arrived"
            db.commit()

        title = (getattr(exhibit, f"title_{language}", None) or exhibit.title_en) if exhibit else None
        return {
            "active": True,
            "blocked_by_tour": False,
            "request_id": nav.id,
            "exhibit_id": nav.target_exhibit_id,
            "exhibit_title": title,
            "exhibit_image": exhibit.image_url if exhibit else None,
            "target_x": float(exhibit.x_position) if exhibit and exhibit.x_position is not None else None,
            "target_y": float(exhibit.y_position) if exhibit and exhibit.y_position is not None else None,
            "status": nav.status,    # in_progress | arrived | cancelled
            "language": language,
        }

    @staticmethod
    def narration(db: Session, request_id: int, with_audio: bool = True) -> dict | None:
        """Narration the robot speaks when it arrives at a single
        (non-tour) exhibit. Same format and language handling as tour."""
        nav = db.query(NavigationRequest).filter(NavigationRequest.id == request_id).first()
        if not nav or nav.status != "arrived":
            return None
        exhibit = db.query(Exhibit).filter(Exhibit.id == nav.target_exhibit_id).first()
        if not exhibit:
            return None
        # Same builder as tour, but `has_more_stops=False` flips to the "last"
        # outro which already asks "any questions before we wrap up?"
        # That works here too.
        lang = "en"   # caller may want to override — passed via API param below
        narration = _build_narration(exhibit, lang, has_more_stops=False)
        audio_b64 = None
        if with_audio:
            try:
                audio_b64 = text_to_speech_base64(narration, lang)
            except Exception as e:
                print(f"[nav] TTS failed: {e}")
        return {
            "exhibit_id": exhibit.id,
            "exhibit_title": getattr(exhibit, f"title_{lang}", None) or exhibit.title_en,
            "narration": narration,
            "has_more_stops": False,
            "language": lang,
            "audio_base64": audio_b64,
        }

    @staticmethod
    def stop(db: Session) -> dict:
        db.query(NavigationRequest).filter(
            NavigationRequest.status == "in_progress"
        ).update({"status": "cancelled"})

        robot = db.query(RobotStatus).first()
        if robot:
            robot.status = "idle"

        db.commit()
        ros_service.cancel_goal()
        return {"message": "Navigation stopped"}

    @staticmethod
    def current_status(db: Session) -> NavigationRequest | None:
        return db.query(NavigationRequest).filter(
            NavigationRequest.status == "in_progress"
        ).order_by(NavigationRequest.created_at.desc()).first()
