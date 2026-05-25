"""
Seed 2 curated preset tours referencing the 3 exhibits from sync_with_simulation.

Run after `sync_with_simulation`:
    python -m app.seed.seed_tours
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.exhibit import Exhibit
from app.models.tour import Tour, TourStop


PRESETS = [
    {
        "name_en": "Highlights Tour",
        "name_ar": "جولة أبرز المعروضات",
        "name_fr": "Visite des points forts",
        "desc_en": "The three most-loved exhibits in 10 minutes. Perfect for a quick visit.",
        "desc_ar": "أكثر ثلاثة معروضات شعبية في 10 دقائق. مثالية للزيارة السريعة.",
        "desc_fr": "Les trois expositions les plus appréciées en 10 minutes. Idéale pour une visite rapide.",
        "minutes": 10,
        "exhibits": ["Golden Mask of Tutankhamun", "Rosetta Stone", "Royal Mummies Chamber"],
    },
    {
        "name_en": "Chronological Journey",
        "name_ar": "رحلة زمنية",
        "name_fr": "Parcours chronologique",
        "desc_en": "Travel through three eras of ancient Egypt — Ptolemaic, then back to the New Kingdom.",
        "desc_ar": "تنقل عبر ثلاث حقب من مصر القديمة — البطلمية، ثم العودة إلى المملكة الحديثة.",
        "desc_fr": "Voyagez à travers trois époques de l'Égypte antique — Ptolémaïque, puis Nouvel Empire.",
        "minutes": 12,
        "exhibits": ["Rosetta Stone", "Golden Mask of Tutankhamun", "Royal Mummies Chamber"],
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        # Wipe existing presets so this is idempotent
        for old in db.query(Tour).filter(Tour.is_preset.is_(True)).all():
            db.delete(old)
        db.flush()

        created = 0
        for p in PRESETS:
            tour = Tour(
                name_en=p["name_en"], name_ar=p["name_ar"], name_fr=p["name_fr"],
                description_en=p["desc_en"], description_ar=p["desc_ar"], description_fr=p["desc_fr"],
                is_preset=True,
                estimated_minutes=p["minutes"],
            )
            db.add(tour)
            db.flush()

            for i, title in enumerate(p["exhibits"]):
                exhibit = (db.query(Exhibit)
                             .filter(Exhibit.title_en.ilike(f"%{title}%"))
                             .first())
                if not exhibit:
                    print(f"  ! Skipped '{title}' — exhibit not found in DB")
                    continue
                db.add(TourStop(
                    tour_id=tour.id,
                    exhibit_id=exhibit.id,
                    sequence_order=i,
                ))

            print(f"  [+] {p['name_en']}  ({len(p['exhibits'])} stops, {p['minutes']} min)")
            created += 1

        db.commit()
        print(f"\nSeeded {created} preset tours.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
