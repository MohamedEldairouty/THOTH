"""
Run with:  python -m app.seed.seed
Seeds the database with sample GEM exhibits, categories, and halls.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.category import Category
from app.models.hall import Hall
from app.models.exhibit import Exhibit


def seed():
    db = SessionLocal()
    try:
        if db.query(Category).count() > 0:
            print("Database already seeded. Skipping.")
            return

        # Categories
        categories = [
            Category(name_en="Statues", name_ar="التماثيل", name_fr="Statues"),
            Category(name_en="Mummies", name_ar="المومياوات", name_fr="Momies"),
            Category(name_en="Jewelry", name_ar="المجوهرات", name_fr="Bijoux"),
            Category(name_en="Papyrus", name_ar="البردي", name_fr="Papyrus"),
            Category(name_en="Sarcophagi", name_ar="التوابيت", name_fr="Sarcophages"),
        ]
        db.add_all(categories)
        db.flush()

        # Halls
        halls = [
            Hall(name_en="Grand Atrium", name_ar="الردهة الكبرى", name_fr="Grand Atrium", floor_number=1),
            Hall(name_en="Tutankhamun Gallery", name_ar="قاعة توتنخامون", name_fr="Galerie Toutânkhamon", floor_number=2),
            Hall(name_en="Royal Mummies Hall", name_ar="قاعة المومياوات الملكية", name_fr="Salle des Momies Royales", floor_number=2),
            Hall(name_en="Ancient Jewelry Hall", name_ar="قاعة المجوهرات القديمة", name_fr="Salle des Bijoux Anciens", floor_number=1),
        ]
        db.add_all(halls)
        db.flush()

        # Exhibits
        exhibits = [
            Exhibit(
                title_en="Golden Mask of Tutankhamun",
                title_ar="القناع الذهبي لتوتنخامون",
                title_fr="Masque en or de Toutânkhamon",
                short_description_en="The iconic golden funerary mask of Pharaoh Tutankhamun.",
                short_description_ar="القناع الجنائزي الذهبي الشهير للفرعون توتنخامون.",
                short_description_fr="Le célèbre masque funéraire en or du pharaon Toutânkhamon.",
                full_description_en="Crafted around 1323 BC, the mask weighs 10.23 kg of solid gold and stands 54 cm tall. It depicts Tutankhamun wearing the nemes headdress with the uraeus and vulture on his forehead, symbolising his dual role as king of Upper and Lower Egypt.",
                full_description_ar="صُنع حوالي عام 1323 قبل الميلاد، يزن القناع 10.23 كيلوجرامًا من الذهب الخالص ويبلغ ارتفاعه 54 سم. يصوّر توتنخامون وهو يرتدي غطاء الرأس 'نمس' مع الكوبرا والنسر على جبهته.",
                full_description_fr="Fabriqué vers 1323 av. J.-C., le masque pèse 10,23 kg d'or massif et mesure 54 cm de hauteur. Il représente Toutânkhamon portant la coiffe nemes avec l'uraeus et le vautour sur son front.",
                era="New Kingdom",
                category_id=categories[2].id,
                hall_id=halls[1].id,
                image_url="/assets/exhibits/tutankhamun_mask.jpg",
                x_position=45.0,
                y_position=30.0,
            ),
            Exhibit(
                title_en="Statue of Ramesses II",
                title_ar="تمثال رمسيس الثاني",
                title_fr="Statue de Ramsès II",
                short_description_en="Colossal statue of Egypt's greatest pharaoh.",
                short_description_ar="تمثال ضخم لأعظم فراعنة مصر.",
                short_description_fr="Statue colossale du plus grand pharaon d'Égypte.",
                full_description_en="This monumental statue of Ramesses II stands over 11 metres tall and weighs approximately 83 tonnes. Originally from the temple complex at Memphis, it dates to the 19th Dynasty (circa 1279–1213 BC).",
                full_description_ar="يبلغ ارتفاع هذا التمثال الضخم لرمسيس الثاني أكثر من 11 مترًا ويزن حوالي 83 طنًا. يعود أصله إلى مجمع المعابد في منف.",
                full_description_fr="Cette statue monumentale de Ramsès II mesure plus de 11 mètres de haut et pèse environ 83 tonnes. Elle provient du complexe du temple de Memphis.",
                era="New Kingdom",
                category_id=categories[0].id,
                hall_id=halls[0].id,
                image_url="/assets/exhibits/ramesses_statue.jpg",
                x_position=20.0,
                y_position=50.0,
            ),
            Exhibit(
                title_en="Book of the Dead Papyrus",
                title_ar="بردية كتاب الموتى",
                title_fr="Papyrus du Livre des Morts",
                short_description_en="Ancient Egyptian funerary text guiding souls through the afterlife.",
                short_description_ar="نص جنائزي مصري قديم يرشد الأرواح عبر الحياة الآخرة.",
                short_description_fr="Texte funéraire égyptien antique guidant les âmes à travers l'au-delà.",
                era="New Kingdom",
                category_id=categories[3].id,
                hall_id=halls[0].id,
                image_url="/assets/exhibits/book_of_dead.jpg",
                x_position=35.0,
                y_position=60.0,
            ),
        ]
        db.add_all(exhibits)

        db.commit()
        print(f"Seeded {len(categories)} categories, {len(halls)} halls, {len(exhibits)} exhibits.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
