"""
Sync the DB exhibits with the simulation team's actual exhibit positions
and names (Tutankhamun, Rosetta Stone, Royal Mummies Chamber).

Run once after pulling the new simulation/maps/map.yaml:
    cd web-app/backend
    source .venv/bin/activate   # or .venv\\Scripts\\activate on Windows
    python -m app.seed.sync_with_simulation
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.exhibit import Exhibit
from app.models.robot import RobotStatus
from app.models.hall import Hall
from app.services.map_service import MapService


# Exhibits matching the simulation team's exhibit_markers_node positions.
# Coordinates are in WORLD meters (map origin is now [-17, -8]).
EXHIBITS = [
    {
        "match_substr": "Tutankhamun",
        "title_en": "Golden Mask of Tutankhamun",
        "title_ar": "القناع الذهبي لتوتنخامون",
        "title_fr": "Masque en or de Toutânkhamon",
        "short_en": "The iconic golden funerary mask of Pharaoh Tutankhamun.",
        "short_ar": "القناع الجنائزي الذهبي الشهير للفرعون توتنخامون.",
        "short_fr": "Le célèbre masque funéraire en or du pharaon Toutânkhamon.",
        "era": "New Kingdom",
        "image_url": "/assets/exhibits/tutankhamun_mask.jpg",
        "x": -2.92494535446167,
        "y":  3.9759843349456787,
    },
    {
        "match_substr": "Ramesses",   # legacy match → will be renamed
        "title_en": "Rosetta Stone",
        "title_ar": "حجر رشيد",
        "title_fr": "Pierre de Rosette",
        "short_en": "The decree of Ptolemy V — the key that unlocked hieroglyphs.",
        "short_ar": "مرسوم بطليموس الخامس — المفتاح الذي فك رموز الهيروغليفية.",
        "short_fr": "Le décret de Ptolémée V — la clé qui a déchiffré les hiéroglyphes.",
        "era": "Ptolemaic",
        "image_url": "/assets/exhibits/rosetta_stone.jpg",
        "x":  2.0068302154541016,
        "y":  0.941784143447876,
    },
    {
        "match_substr": "Book of",   # legacy match → will be renamed
        "title_en": "Royal Mummies Chamber",
        "title_ar": "قاعة المومياوات الملكية",
        "title_fr": "Salle des Momies Royales",
        "short_en": "The preserved remains of pharaohs who ruled Egypt three millennia ago.",
        "short_ar": "بقايا الفراعنة الذين حكموا مصر منذ ثلاثة آلاف عام.",
        "short_fr": "Les restes préservés des pharaons qui régnaient sur l'Égypte il y a trois millénaires.",
        "era": "New Kingdom",
        "image_url": "/assets/exhibits/royal_mummies.jpg",
        "x":  5.001344680786133,
        "y": -2.0101232528686523,
    },
]


def main() -> None:
    cfg = MapService.get_map_config()
    print(f"Map: {cfg['width_m']:.1f}m × {cfg['height_m']:.1f}m "
          f"(origin world coord = {cfg['origin_x']:.1f}, {cfg['origin_y']:.1f})")
    print()

    db = SessionLocal()
    try:
        updated = created = 0

        for ex in EXHIBITS:
            # Try to match by either the new title (re-runs) or the legacy substring
            row = (db.query(Exhibit)
                     .filter(Exhibit.title_en == ex["title_en"])
                     .first())
            if row is None:
                row = (db.query(Exhibit)
                         .filter(Exhibit.title_en.ilike(f"%{ex['match_substr']}%"))
                         .first())

            if row is None:
                # No legacy row — create a fresh one
                row = Exhibit()
                db.add(row)
                created += 1
                print(f"  [+] Creating: {ex['title_en']}")
            else:
                updated += 1
                print(f"  [~] Updating: {row.title_en} → {ex['title_en']}")

            # Re-write the localized titles + short descriptions + position
            row.title_en = ex["title_en"]
            row.title_ar = ex["title_ar"]
            row.title_fr = ex["title_fr"]
            row.short_description_en = ex["short_en"]
            row.short_description_ar = ex["short_ar"]
            row.short_description_fr = ex["short_fr"]
            row.era = ex["era"]
            row.image_url = ex["image_url"]
            row.x_position = ex["x"]
            row.y_position = ex["y"]

        # Move the robot home pose to (0, 0) — center of the new map
        robot = db.query(RobotStatus).first()
        if robot:
            robot.current_x = 0.0
            robot.current_y = 0.0
            robot.status = "idle"
            print(f"\n  [~] Robot home → (0.0 m, 0.0 m)")

        db.commit()
        print(f"\nDone. {updated} updated, {created} created.")
        print("\nDB exhibits now match simulation/simulate_robot_pkg/exhibit_markers_node.py")
    finally:
        db.close()


if __name__ == "__main__":
    main()
