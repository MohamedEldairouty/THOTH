"""
One-off migration: switch the existing exhibit + robot positions from
arbitrary 0..100 percentages to REAL world coordinates (meters), aligned
to the ROS Nav2 map (map.yaml, 34m x 16m, resolution 0.05).

Run once:
    cd web-app/backend
    .venv\\Scripts\\activate
    python -m app.seed.reposition_to_world_coords
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.exhibit import Exhibit
from app.models.robot import RobotStatus
from app.services.map_service import MapService

# Hand-picked spots that look walkable on the themed map.
# (We'll refine these by sampling the PGM later — for now, decent enough
# that the markers don't sit on a wall.)
TARGETS = {
    # title_en substring  ->  (world_x, world_y) in meters
    "Tutankhamun":   (32.5, 7.5),
    "Ramesses":      ( 12.0, 1.0),
    "Book of":       (24.5, 1.0),
}


def main() -> None:
    cfg = MapService.get_map_config()
    print(f"Map: {cfg['width_m']:.1f}m x {cfg['height_m']:.1f}m ({cfg['width_px']}x{cfg['height_px']} px @ {cfg['resolution']} m/px)")

    db = SessionLocal()
    try:
        updated = 0
        for exhibit in db.query(Exhibit).all():
            for needle, (wx, wy) in TARGETS.items():
                if needle.lower() in exhibit.title_en.lower():
                    exhibit.x_position = wx
                    exhibit.y_position = wy
                    print(f"  Exhibit #{exhibit.id} ({exhibit.title_en[:30]}) -> ({wx} m, {wy} m)")
                    updated += 1
                    break
        # Move robot to a sensible starting pose near the entrance
        robot = db.query(RobotStatus).first()
        if robot:
            robot.current_x = 3.0
            robot.current_y = 3.0
            print(f"  Robot -> (3.0 m, 3.0 m)")

        db.commit()
        print(f"Updated {updated} exhibits.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
