"""Map service — loads the ROS Nav2 map.yaml so the frontend can convert
world coordinates (meters) to screen percentages, and vice-versa."""

import os
from functools import lru_cache
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models.exhibit import Exhibit


# ──────────────────────────────────────────────────────────────
# Map metadata (cached — read once at startup)
# ──────────────────────────────────────────────────────────────

# The frontend serves the themed PNG from public/assets/museum_map.png
MAP_IMAGE_URL = "/assets/museum_map.png"

# The source of truth for resolution / origin / dimensions
# is the ROS Nav2 map.yaml from the simulation team.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent.parent  # web-app/backend/.. => web-app => ..
MAP_YAML_PATH = _PROJECT_ROOT / "simulation" / "maps" / "map.yaml"


@lru_cache(maxsize=1)
def _load_map_config() -> dict:
    """Read map.yaml + PGM header. Returns:
        {
          resolution: float (m/pixel),
          origin_x, origin_y: floats (world coords of map bottom-left),
          width_px, height_px: ints,
          width_m, height_m: floats,
        }
    Falls back to hard-coded defaults if the yaml can't be read so the
    backend still starts in environments where the simulation folder isn't present.
    """
    defaults = {
        "resolution": 0.05,
        "origin_x": 0.0,
        "origin_y": 0.0,
        "width_px": 680,
        "height_px": 320,
        "width_m": 34.0,
        "height_m": 16.0,
    }

    if not MAP_YAML_PATH.exists():
        return defaults

    try:
        with open(MAP_YAML_PATH, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}

        resolution = float(doc.get("resolution", 0.05))
        origin = doc.get("origin", [0.0, 0.0, 0.0])
        origin_x, origin_y = float(origin[0]), float(origin[1])

        # Read PGM header to get dimensions (no PIL dependency required)
        pgm_path = MAP_YAML_PATH.parent / doc.get("image", "map.pgm")
        width_px, height_px = _read_pgm_dimensions(pgm_path) or (680, 320)

        return {
            "resolution": resolution,
            "origin_x": origin_x,
            "origin_y": origin_y,
            "width_px": width_px,
            "height_px": height_px,
            "width_m": width_px * resolution,
            "height_m": height_px * resolution,
        }
    except Exception:
        return defaults


def _read_pgm_dimensions(path: Path) -> tuple[int, int] | None:
    """Parse the small ASCII header of a binary PGM (P5) to get (w, h)."""
    try:
        with open(path, "rb") as f:
            tokens: list[bytes] = []
            buf = b""
            while len(tokens) < 3:
                ch = f.read(1)
                if not ch:
                    return None
                if ch in (b" ", b"\t", b"\n", b"\r"):
                    if buf:
                        if not buf.startswith(b"#"):
                            tokens.append(buf)
                        buf = b""
                elif ch == b"#":
                    f.readline()  # skip comment
                else:
                    buf += ch
            magic, w, h = tokens
            return int(w), int(h)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────────────────────


class MapService:
    @staticmethod
    def get_map_config() -> dict:
        return _load_map_config()

    @staticmethod
    def get_map_overview(db: Session) -> dict:
        from app.services import ros_service
        x, y, _yaw = ros_service.get_pose()
        return {
            "map_image_url": MAP_IMAGE_URL,
            "map_config": _load_map_config(),
            "robot": {
                "x": x,
                "y": y,
                "status": ros_service.get_status(),
            },
        }

    @staticmethod
    def get_exhibit_positions(db: Session, lang: str) -> list[dict]:
        exhibits = (
            db.query(Exhibit)
            .filter(Exhibit.x_position.isnot(None), Exhibit.y_position.isnot(None))
            .all()
        )
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
