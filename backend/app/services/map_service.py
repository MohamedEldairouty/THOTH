from sqlalchemy.orm import Session

from app.models.exhibit import Exhibit
from app.models.robot import RobotStatus


class MapService:
    @staticmethod
    def get_map_overview(db: Session) -> dict:
        robot = db.query(RobotStatus).first()
        return {
            "map_image_url": "/assets/museum_map.png",
            "robot": {
                "x": robot.current_x if robot else 0.0,
                "y": robot.current_y if robot else 0.0,
                "status": robot.status if robot else "offline",
            },
        }

    @staticmethod
    def get_exhibit_positions(db: Session, lang: str) -> list[dict]:
        exhibits = db.query(Exhibit).filter(
            Exhibit.x_position.isnot(None), Exhibit.y_position.isnot(None)
        ).all()
        return [
            {
                "id": e.id,
                "title": getattr(e, f"title_{lang}") or e.title_en,
                "x": e.x_position,
                "y": e.y_position,
                "hall_id": e.hall_id,
            }
            for e in exhibits
        ]

    @staticmethod
    def get_route(db: Session, from_exhibit: int | None, to_exhibit: int) -> dict:
        target = db.query(Exhibit).filter(Exhibit.id == to_exhibit).first()
        return {
            "simulated": True,
            "from_exhibit_id": from_exhibit,
            "to_exhibit_id": to_exhibit,
            "target_x": target.x_position if target else None,
            "target_y": target.y_position if target else None,
            "waypoints": [],
            "estimated_time_seconds": 30,
        }
