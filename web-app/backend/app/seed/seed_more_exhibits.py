"""
Add 8 more famous GEM (Grand Egyptian Museum) exhibits to the DB.

Sources: gem.eg/collection/artefacts/, Egyptian Museum collections,
public records of GEM's permanent exhibition.

Positions are picked to be spread across the map area. Some may land on
walls in the campus floorplan — use RViz's /clicked_point to verify
each position is walkable, then update via this script and re-run.

This script is idempotent — re-runs update existing rows (matched by
title_en) rather than duplicating.

Run:
    cd web-app/backend
    source .venv/bin/activate
    python -m app.seed.seed_more_exhibits
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.exhibit import Exhibit
from app.models.category import Category
from app.models.hall import Hall


# All 3 dimensions: famous GEM exhibits with full multilingual data.
# Coordinates are world meters (map origin = -17, -8; map = 34m × 16m).
EXHIBITS = [
    {
        "title_en": "Colossal Statue of Ramesses II",
        "title_ar": "تمثال رمسيس الثاني الضخم",
        "title_fr": "Statue colossale de Ramsès II",
        "short_en": "An 11-metre, 83-ton granite giant greeting visitors at the Grand Atrium.",
        "short_ar": "عملاق جرانيتي بطول 11 متراً ووزن 83 طناً يستقبل الزوار في الردهة الكبرى.",
        "short_fr": "Un géant de granit de 11 mètres et 83 tonnes accueillant les visiteurs au Grand Atrium.",
        "full_en": "Carved from a single block of red granite around 1250 BC, the colossus of Ramesses II stood for centuries at the Memphis temple complex before being moved to the heart of the Grand Egyptian Museum. The 83-ton statue depicts Egypt's most prolific pharaoh in a striding pose, wearing the white crown of Upper Egypt. It is the first artefact visitors encounter as they enter the museum.",
        "full_ar": "نُحت من كتلة واحدة من الجرانيت الأحمر حوالي عام 1250 قبل الميلاد، وقف التمثال الضخم لرمسيس الثاني لقرون في مجمع معابد منف قبل نقله إلى قلب المتحف المصري الكبير. يصور التمثال الذي يزن 83 طناً أكثر فراعنة مصر إنتاجاً في وضعية المشي، مرتدياً التاج الأبيض للوجه القبلي.",
        "full_fr": "Sculpté dans un seul bloc de granit rouge vers 1250 av. J.-C., le colosse de Ramsès II s'est dressé pendant des siècles au complexe du temple de Memphis avant d'être déplacé au cœur du Grand Musée Égyptien. La statue de 83 tonnes représente le pharaon le plus prolifique d'Égypte en position de marche, portant la couronne blanche de Haute-Égypte.",
        "era": "New Kingdom",
        "category": "Statues",
        "hall": "Grand Atrium",
        "image_url": "/assets/exhibits/ramesses_statue.jpg",
        "x": -10.0, "y": 4.0,
    },
    {
        "title_en": "Throne of Tutankhamun",
        "title_ar": "عرش توتنخامون",
        "title_fr": "Trône de Toutânkhamon",
        "short_en": "A gilded wooden throne showing the boy king with his queen Ankhesenamun.",
        "short_ar": "عرش خشبي مذهب يصور الملك الصبي مع زوجته عنخ إسن آمون.",
        "short_fr": "Un trône en bois doré représentant le jeune roi avec sa reine Ânkhésenamon.",
        "full_en": "One of the most exquisite objects from Tutankhamun's tomb, this golden throne is overlaid with sheet gold and inlaid with semi-precious stones, coloured glass and faience. The backrest depicts an intimate domestic scene — Queen Ankhesenamun anointing the young pharaoh under the rays of the Aten sun-disc, a holdover from the Amarna religious revolution.",
        "full_ar": "واحد من أرقى القطع من مقبرة توتنخامون، هذا العرش الذهبي مغطى بصفائح ذهبية ومرصع بأحجار شبه كريمة وزجاج ملون. يصور مسند الظهر مشهداً عائلياً حميماً للملكة عنخ إسن آمون وهي تدهن الفرعون الشاب تحت أشعة قرص الشمس آتون.",
        "full_fr": "L'un des objets les plus exquis du tombeau de Toutânkhamon, ce trône doré est recouvert de feuilles d'or et incrusté de pierres semi-précieuses, de verre coloré et de faïence. Le dossier représente une scène domestique intime — la reine Ânkhésenamon oignant le jeune pharaon sous les rayons du disque solaire Aton.",
        "era": "New Kingdom",
        "category": "Jewelry",
        "hall": "Tutankhamun Gallery",
        "image_url": "/assets/exhibits/tut_throne.jpg",
        "x": -6.0, "y": 5.5,
    },
    {
        "title_en": "Anubis Shrine",
        "title_ar": "مقصورة أنوبيس",
        "title_fr": "Châsse d'Anubis",
        "short_en": "A life-sized statue of the jackal-headed god, guardian of Tutankhamun's burial.",
        "short_ar": "تمثال بالحجم الطبيعي للإله ذي رأس ابن آوى، حارس دفن توتنخامون.",
        "short_fr": "Une statue grandeur nature du dieu à tête de chacal, gardien de la sépulture de Toutânkhamon.",
        "full_en": "Discovered guarding the entrance to the treasury chamber of Tutankhamun's tomb, this gilded wooden Anubis sits atop a portable shrine. Anubis was the god of mummification and the afterlife, and his vigilant pose embodies the protection the deceased pharaoh would need on his journey through the underworld.",
        "full_ar": "اكتُشف وهو يحرس مدخل غرفة الكنز في مقبرة توتنخامون، يجلس أنوبيس الخشبي المذهب فوق مقصورة محمولة. كان أنوبيس إله التحنيط والحياة الآخرة، ويجسد وضعه اليقظ الحماية التي يحتاجها الفرعون المتوفى في رحلته عبر العالم السفلي.",
        "full_fr": "Découvert gardant l'entrée de la chambre du trésor du tombeau de Toutânkhamon, cet Anubis en bois doré est assis sur un sanctuaire portatif. Anubis était le dieu de la momification et de l'au-delà, et sa pose vigilante incarne la protection dont le pharaon défunt aurait besoin pour son voyage dans les enfers.",
        "era": "New Kingdom",
        "category": "Sarcophagi",
        "hall": "Tutankhamun Gallery",
        "image_url": "/assets/exhibits/anubis_shrine.jpg",
        "x": -3.0, "y": -5.0,
    },
    {
        "title_en": "Tutankhamun's Coffins",
        "title_ar": "توابيت توتنخامون",
        "title_fr": "Cercueils de Toutânkhamon",
        "short_en": "Three nested coffins — the innermost made of 110 kg of solid gold.",
        "short_ar": "ثلاثة توابيت متداخلة — أصغرها مصنوع من 110 كيلوغرامات من الذهب الخالص.",
        "short_fr": "Trois cercueils emboîtés — le plus intérieur est en or massif de 110 kg.",
        "full_en": "Tutankhamun's mummy was placed inside three coffins nested one within the other. The outer two are made of gilded wood inlaid with coloured glass, while the innermost coffin is wrought from 110 kilograms of solid gold — depicting the young pharaoh holding the crook and flail, with the wings of Nekhbet and Wadjet protecting him.",
        "full_ar": "وُضعت مومياء توتنخامون داخل ثلاثة توابيت متداخلة. التابوتان الخارجيان مصنوعان من الخشب المذهب المرصع بالزجاج الملون، بينما التابوت الداخلي مصنوع من 110 كيلوغرامات من الذهب الخالص — يصور الفرعون الشاب ممسكاً بالعصا والمذبة.",
        "full_fr": "La momie de Toutânkhamon a été placée dans trois cercueils emboîtés les uns dans les autres. Les deux extérieurs sont en bois doré incrusté de verre coloré, tandis que le plus intérieur est forgé dans 110 kilogrammes d'or massif — représentant le jeune pharaon tenant le crochet et le fléau.",
        "era": "New Kingdom",
        "category": "Sarcophagi",
        "hall": "Tutankhamun Gallery",
        "image_url": "/assets/exhibits/tut_coffins.jpg",
        "x": 3.0, "y": 5.0,
    },
    {
        "title_en": "Hatshepsut Seated Statue",
        "title_ar": "تمثال حتشبسوت الجالسة",
        "title_fr": "Statue assise d'Hatchepsout",
        "short_en": "Limestone statue of the female pharaoh who ruled Egypt for over two decades.",
        "short_ar": "تمثال من الحجر الجيري للملكة الفرعونية التي حكمت مصر لأكثر من عقدين.",
        "short_fr": "Statue en calcaire de la pharaonne qui a régné sur l'Égypte pendant plus de deux décennies.",
        "full_en": "Hatshepsut was one of ancient Egypt's most successful rulers, reigning as pharaoh for over 20 years during the 18th Dynasty. This limestone statue from her mortuary temple at Deir el-Bahari shows her seated in formal regalia. After her death, her successor Thutmose III ordered many of her statues destroyed — making each surviving piece historically priceless.",
        "full_ar": "كانت حتشبسوت من أنجح حكام مصر القديمة، حيث حكمت كفرعون لأكثر من 20 عاماً خلال الأسرة الثامنة عشرة. يظهرها هذا التمثال من الحجر الجيري من معبدها الجنائزي في الدير البحري جالسة في زينة رسمية. بعد وفاتها، أمر خلفها تحتمس الثالث بتدمير العديد من تماثيلها.",
        "full_fr": "Hatchepsout fut l'une des dirigeantes les plus réussies de l'Égypte antique, régnant comme pharaon pendant plus de 20 ans durant la 18e dynastie. Cette statue en calcaire de son temple funéraire de Deir el-Bahari la montre assise en tenue formelle. Après sa mort, son successeur Thoutmôsis III ordonna la destruction de nombre de ses statues.",
        "era": "New Kingdom",
        "category": "Statues",
        "hall": "Grand Atrium",
        "image_url": "/assets/exhibits/hatshepsut.jpg",
        "x": 8.0, "y": 3.0,
    },
    {
        "title_en": "Yuya and Tjuyu Funerary Collection",
        "title_ar": "مجموعة يويا وتويا الجنائزية",
        "title_fr": "Collection funéraire de Youya et Touya",
        "short_en": "The intact burial of Tutankhamun's great-grandparents — discovered 1905.",
        "short_ar": "الدفن السليم لجد وجدة توتنخامون الكبيرين — اكتُشف عام 1905.",
        "short_fr": "La sépulture intacte des arrière-grands-parents de Toutânkhamon — découverte en 1905.",
        "full_en": "Until Tutankhamun was found in 1922, the tomb of Yuya and Tjuyu was the most intact royal burial ever discovered. The parents of Queen Tiye and great-grandparents of Tutankhamun, they were given an extraordinary funerary collection: gilded coffins, jewellery, chariots, and one of the earliest known examples of a complete papyrus Book of the Dead.",
        "full_ar": "حتى اكتشاف توتنخامون عام 1922، كانت مقبرة يويا وتويا أكثر دفن ملكي سليم تم اكتشافه على الإطلاق. كوالدي الملكة تي وجد وجدة توتنخامون الكبيرين، حصلا على مجموعة جنائزية استثنائية: توابيت مذهبة، ومجوهرات، ومركبات.",
        "full_fr": "Jusqu'à la découverte de Toutânkhamon en 1922, la tombe de Youya et Touya était la sépulture royale la plus intacte jamais découverte. Parents de la reine Tiyi et arrière-grands-parents de Toutânkhamon, ils ont reçu une collection funéraire extraordinaire : cercueils dorés, bijoux, chars.",
        "era": "New Kingdom",
        "category": "Mummies",
        "hall": "Royal Mummies Hall",
        "image_url": "/assets/exhibits/yuya_tjuyu.jpg",
        "x": 10.0, "y": -2.0,
    },
    {
        "title_en": "Bust of Akhenaten",
        "title_ar": "تمثال نصفي لأخناتون",
        "title_fr": "Buste d'Akhenaton",
        "short_en": "The revolutionary pharaoh who introduced monotheism — rendered in the Amarna style.",
        "short_ar": "الفرعون الثوري الذي أدخل التوحيد — مصور بالأسلوب العمرني.",
        "short_fr": "Le pharaon révolutionnaire qui a introduit le monothéisme — rendu dans le style amarnien.",
        "full_en": "Akhenaten (formerly Amenhotep IV) shattered 1,500 years of Egyptian religious tradition by abolishing the polytheistic pantheon and worshipping a single solar deity, the Aten. The art of his reign — the Amarna style — broke with rigid royal conventions, depicting figures with elongated faces, narrow shoulders, and prominent bellies, as seen in this striking sandstone bust.",
        "full_ar": "حطم أخناتون (أمنحتب الرابع سابقاً) 1500 عام من التقليد الديني المصري بإلغاء الآلهة المتعددة وعبادة إله شمسي واحد، آتون. كسر فن عهده — الأسلوب العمرني — التقاليد الملكية الصارمة، مصوراً الشخصيات بوجوه ممدودة وأكتاف ضيقة وبطون بارزة.",
        "full_fr": "Akhenaton (anciennement Amenhotep IV) a brisé 1 500 ans de tradition religieuse égyptienne en abolissant le panthéon polythéiste et en adorant une divinité solaire unique, Aton. L'art de son règne — le style amarnien — a rompu avec les conventions royales rigides.",
        "era": "Amarna Period",
        "category": "Statues",
        "hall": "Tutankhamun Gallery",
        "image_url": "/assets/exhibits/akhenaten_bust.jpg",
        "x": -8.0, "y": 1.5,
    },
    {
        "title_en": "Book of the Dead Papyrus",
        "title_ar": "بردية كتاب الموتى",
        "title_fr": "Papyrus du Livre des Morts",
        "short_en": "Spells and instructions to guide the deceased safely through the afterlife.",
        "short_ar": "تعاويذ وإرشادات لتوجيه المتوفى بأمان عبر الحياة الآخرة.",
        "short_fr": "Sorts et instructions pour guider le défunt en sécurité à travers l'au-delà.",
        "full_en": "The Book of the Dead is a collection of nearly 200 magical spells, hymns, and prayers placed in the tombs of well-off ancient Egyptians from around 1550 BC onwards. The most famous spell is the Weighing of the Heart — where the deceased's heart is balanced against the feather of Ma'at, goddess of truth. A heart lighter than the feather granted entry to the afterlife.",
        "full_ar": "كتاب الموتى مجموعة من حوالي 200 تعويذة سحرية وترانيم وصلوات وُضعت في مقابر المصريين القدماء الميسورين منذ حوالي 1550 قبل الميلاد. أشهر التعاويذ هي وزن القلب — حيث يُوزن قلب المتوفى مقابل ريشة ماعت إلهة الحقيقة.",
        "full_fr": "Le Livre des Morts est un recueil de près de 200 sorts magiques, hymnes et prières placés dans les tombes des anciens Égyptiens aisés à partir d'environ 1550 av. J.-C. Le sort le plus célèbre est la Pesée du Cœur — où le cœur du défunt est mis en balance avec la plume de Maât.",
        "era": "New Kingdom",
        "category": "Papyrus",
        "hall": "Grand Atrium",
        "image_url": "/assets/exhibits/book_of_dead.jpg",
        "x": 6.0, "y": 1.5,
    },
]


def _find_or_first(db, model, **filters):
    q = db.query(model)
    for k, v in filters.items():
        q = q.filter(getattr(model, k).ilike(f"%{v}%"))
    return q.first()


def main() -> None:
    db = SessionLocal()
    try:
        added = updated = 0
        for ex in EXHIBITS:
            category = _find_or_first(db, Category, name_en=ex["category"])
            hall = _find_or_first(db, Hall, name_en=ex["hall"])

            row = (db.query(Exhibit)
                     .filter(Exhibit.title_en == ex["title_en"])
                     .first())
            if row is None:
                row = Exhibit()
                db.add(row)
                added += 1
                action = "[+]"
            else:
                updated += 1
                action = "[~]"

            row.title_en, row.title_ar, row.title_fr = ex["title_en"], ex["title_ar"], ex["title_fr"]
            row.short_description_en = ex["short_en"]
            row.short_description_ar = ex["short_ar"]
            row.short_description_fr = ex["short_fr"]
            row.full_description_en = ex["full_en"]
            row.full_description_ar = ex["full_ar"]
            row.full_description_fr = ex["full_fr"]
            row.era = ex["era"]
            row.category_id = category.id if category else None
            row.hall_id = hall.id if hall else None
            row.image_url = ex["image_url"]
            row.x_position = ex["x"]
            row.y_position = ex["y"]

            print(f"  {action} {ex['title_en']:42s}  ({ex['x']:+5.1f}, {ex['y']:+5.1f})  → {ex['category']}")

        db.commit()
        print(f"\nDone. {added} added, {updated} updated.")
        print(f"Total exhibits in DB: {db.query(Exhibit).count()}")
        print("\nNote: positions are approximate — test each one in RViz with 'Nav2 Goal'")
        print("       and re-run this script if a position lands on a wall.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
