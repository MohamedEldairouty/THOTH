"""
Three preset tours over the 6 exhibits from seed_exhibits.

Tour A — Grand Tour: all 6 exhibits, roughly 20 minutes
Tour B — Royal Highlights: 3 most-iconic royal artefacts
Tour C — Artistry & Craft: 3 exhibits showcasing ancient Egyptian craftsmanship

Run AFTER seed_exhibits:
    python -m app.seed.seed_tours
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import text

from app.database import SessionLocal
from app.models.exhibit import Exhibit
from app.models.tour import Tour, TourStop


PRESETS = [
    {
        "name_en": "Grand Tour",
        "name_ar": "الجولة الكبرى",
        "name_fr": "Grand Parcours",
        "desc_en": "Visit all six headline artefacts — the complete THOTH experience.",
        "desc_ar": "زر جميع القطع الست الرئيسية — تجربة تحوت الكاملة.",
        "desc_fr": "Visitez les six artefacts phares — l'expérience THOTH complète.",
        "minutes": 20,
        "exhibits": [
            "Colossal Statue of Ramesses II",
            "Golden Burial Mask of Tutankhamun",
            "Seated Statue of Thutmose III",
            "Head of King Amenhotep III",
            "Statue of the Scribe Mitri",
            "Statuette of a Falcon",
        ],
    },
    {
        "name_en": "Royal Highlights",
        "name_ar": "أبرز الملوك",
        "name_fr": "Points forts royaux",
        "desc_en": "Three iconic depictions of Egypt's greatest pharaohs in 10 minutes.",
        "desc_ar": "ثلاثة تصويرات أيقونية لأعظم فراعنة مصر في 10 دقائق.",
        "desc_fr": "Trois représentations emblématiques des plus grands pharaons d'Égypte en 10 minutes.",
        "minutes": 10,
        "exhibits": [
            "Colossal Statue of Ramesses II",
            "Golden Burial Mask of Tutankhamun",
            "Seated Statue of Thutmose III",
        ],
    },
    {
        "name_en": "Artistry & Craft",
        "name_ar": "الفن والحرفية",
        "name_fr": "Art et Artisanat",
        "desc_en": "Three exhibits that showcase the artistic mastery of ancient Egypt.",
        "desc_ar": "ثلاث معروضات تستعرض البراعة الفنية لمصر القديمة.",
        "desc_fr": "Trois expositions qui mettent en valeur la maîtrise artistique de l'Égypte antique.",
        "minutes": 10,
        "exhibits": [
            "Head of King Amenhotep III",
            "Statue of the Scribe Mitri",
            "Statuette of a Falcon",
        ],
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        # Wipe runtime tour state first — TourRun rows reference Tour by FK,
        # so they must go before we can delete the tours themselves.
        db.execute(text("DELETE FROM tour_runs"))
        db.execute(text("DELETE FROM tour_stops"))
        db.flush()

        # Wipe any existing preset tours so this is idempotent
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

            stop_count = 0
            for i, title in enumerate(p["exhibits"]):
                exhibit = (db.query(Exhibit)
                             .filter(Exhibit.title_en.ilike(f"%{title}%"))
                             .first())
                if not exhibit:
                    print(f"  ! Skipped '{title}' -- exhibit not found in DB")
                    continue
                db.add(TourStop(
                    tour_id=tour.id,
                    exhibit_id=exhibit.id,
                    sequence_order=i,
                ))
                stop_count += 1

            print(f"  [+] {p['name_en']:22s}  {stop_count} stops * ~{p['minutes']} min")
            created += 1

        db.commit()
        print(f"\nSeeded {created} preset tours.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
