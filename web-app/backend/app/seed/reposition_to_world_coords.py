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

# Real positions taken from /clicked_point in RViz by the simulation team,
# matching the 3 exhibit markers their exhibit_markers_node publishes.
# Map origin is now [-17.0, -8.0] (centered), so these are world coords.
TARGETS = {
    # title_en substring  ->  (world_x, world_y) in meters
    "Tutankhamun":     (-2.92494535446167,  3.9759843349456787),
    "Rosetta":         ( 2.0068302154541016, 0.941784143447876),
    "Royal Mummies":   ( 5.001344680786133, -2.0101232528686523),
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
