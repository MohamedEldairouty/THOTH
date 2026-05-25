"""
Single authoritative source of all THOTH exhibits.

6 real GEM artefacts with full multilingual data.

Two of the positions are verified walkable (the sim team picked them via
RViz /clicked_point); the other four are educated guesses. On Ubuntu,
use RViz's "Publish Point" tool to refine any position that turns out
to land on a wall, then re-run this script.

Run:
    cd web-app/backend
    source .venv/bin/activate          (or .venv\\Scripts\\activate on Windows)
    python -m app.seed.seed_exhibits
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import text

from app.database import SessionLocal
from app.models.exhibit import Exhibit
from app.models.category import Category
from app.models.hall import Hall


# ─────────────────────────────────────────────────────────────────────
# The 6 final exhibits.
# Map origin = (-17, -8) → world bounds: x in [-17, 17], y in [-8, 8]
# ─────────────────────────────────────────────────────────────────────

EXHIBITS = [
    # ─── 1. Tutankhamun's Golden Mask ────────────────────────────────
    {
        "title_en": "The Golden Burial Mask of Tutankhamun",
        "title_ar": "القناع الذهبي الجنائزي لتوتنخامون",
        "title_fr": "Le Masque funéraire d'or de Toutânkhamon",
        "short_en": "The iconic 11-kg solid-gold mask that covered the boy king's mummy.",
        "short_ar": "القناع الأيقوني المصنوع من 11 كجم من الذهب الخالص الذي غطى مومياء الملك الصبي.",
        "short_fr": "Le célèbre masque en or massif de 11 kg qui couvrait la momie du jeune roi.",
        "full_en": "Crafted from over 10 kg of solid gold around 1323 BC, this mask covered the head of the mummified pharaoh Tutankhamun. The face is inlaid with semi-precious stones — lapis lazuli for the eyebrows, obsidian for the pupils, and quartz for the whites of the eyes. It wears the nemes headcloth and is flanked by the vulture and cobra goddesses Nekhbet and Wadjet, protectors of Upper and Lower Egypt.",
        "full_ar": "صُنع هذا القناع من أكثر من 10 كجم من الذهب الخالص حوالي عام 1323 قبل الميلاد، وقد غطى رأس مومياء الفرعون توتنخامون. الوجه مرصع بأحجار شبه كريمة — اللازورد للحاجبين، والأوبسيديان للحدقتين، والكوارتز للبياض. يرتدي غطاء الرأس النمس وتحيط به ربتي الحماية نخبت وواجت.",
        "full_fr": "Confectionné dans plus de 10 kg d'or massif vers 1323 av. J.-C., ce masque couvrait la tête du pharaon momifié Toutânkhamon. Le visage est incrusté de pierres semi-précieuses — du lapis-lazuli pour les sourcils, de l'obsidienne pour les pupilles, et du quartz pour le blanc des yeux. Il porte la coiffe némès, flanqué des déesses Nekhbet et Ouadjet.",
        "era": "New Kingdom",
        "category": "Jewelry",
        "hall": "Tutankhamun Gallery",
        "image_url": "/assets/exhibits/tutankhamun_mask.jpg",
        "x": -2.92, "y": 3.98,                  # ✓ verified walkable
        "verified": True,
    },

    # ─── 2. Colossal Statue of Ramesses II ───────────────────────────
    {
        "title_en": "Colossal Statue of Ramesses II",
        "title_ar": "تمثال رمسيس الثاني الضخم",
        "title_fr": "Statue colossale de Ramsès II",
        "short_en": "An 11-metre, 83-ton granite giant greeting visitors in the Grand Atrium.",
        "short_ar": "عملاق جرانيتي بطول 11 متراً ووزن 83 طناً يستقبل الزوار في الردهة الكبرى.",
        "short_fr": "Un géant de granit de 11 mètres et 83 tonnes accueillant les visiteurs au Grand Atrium.",
        "full_en": "Carved from a single block of red granite around 1250 BC, this colossus of Ramesses II stood for centuries at the Memphis temple complex before being moved to the heart of the Grand Egyptian Museum. The 83-ton, 11-metre statue depicts Egypt's most prolific pharaoh in a striding pose. It is the first artefact visitors encounter as they enter the museum.",
        "full_ar": "نُحت من كتلة واحدة من الجرانيت الأحمر حوالي عام 1250 قبل الميلاد، وقف هذا التمثال الضخم لرمسيس الثاني لقرون في مجمع معابد منف قبل نقله إلى قلب المتحف المصري الكبير. يصور التمثال الذي يبلغ طوله 11 متراً ويزن 83 طناً أكثر فراعنة مصر إنتاجاً في وضعية المشي.",
        "full_fr": "Sculpté dans un seul bloc de granit rouge vers 1250 av. J.-C., ce colosse de Ramsès II s'est dressé pendant des siècles au complexe du temple de Memphis avant d'être déplacé au cœur du Grand Musée Égyptien. La statue de 83 tonnes et 11 mètres représente le pharaon le plus prolifique d'Égypte en position de marche.",
        "era": "New Kingdom",
        "category": "Statues",
        "hall": "Grand Atrium",
        "image_url": "/assets/exhibits/ramesses_statue.jpg",
        "x": 2.01, "y": 0.94,                   # ✓ verified walkable (re-used)
        "verified": True,
    },

    # ─── 3. Statuette of a Falcon (Horus) ────────────────────────────
    {
        "title_en": "Statuette of a Falcon",
        "title_ar": "تمثال صغير للصقر",
        "title_fr": "Statuette d'un faucon",
        "short_en": "A gilt bronze votive falcon — the avian form of the god Horus.",
        "short_ar": "تمثال نذري صغير من البرونز المذهب — الشكل الطيري للإله حورس.",
        "short_fr": "Une statuette votive en bronze doré — la forme aviaire du dieu Horus.",
        "full_en": "Discovered in 1893 at Sais in the western Delta and dated to Dynasty 26, this gilt bronze votive statuette was made using the lost-wax technique — a wax model was enclosed in clay, melted out, and replaced with molten metal. Gold highlights the falcon's head, plumage, and jewellery. Depicting Horus, the god of kingship, the falcon wears a crown and a broad gilded collar ending in a solar-heart amulet. The dedicatory text on the base names Imhotep, son of Padineith, who donated it so he could magically share in temple rituals he wasn't allowed to attend in person.",
        "full_ar": "اكتُشف هذا التمثال النذري الصغير المصنوع من البرونز المذهب عام 1893 في سايس بالدلتا الغربية ويرجع تاريخه إلى الأسرة 26. صُنع باستخدام تقنية الشمع المفقود — حيث يُحاط نموذج من الشمع بالطين، ثم يُذاب ويُستبدل بالمعدن المنصهر. يُبرز الذهب رأس الصقر وريشه ومجوهراته. يصور حورس إله الملوكية، يرتدي تاجاً وقلادة عريضة مذهبة تنتهي بتميمة قلب الشمس.",
        "full_fr": "Découverte en 1893 à Saïs dans le Delta occidental et datée de la 26e dynastie, cette statuette votive en bronze doré a été fabriquée par la technique de la cire perdue — un modèle en cire enfermé dans l'argile, fondu, puis remplacé par du métal en fusion. L'or rehausse la tête, le plumage et les bijoux du faucon. Représentant Horus, le dieu de la royauté, le faucon porte une couronne et un large collier doré se terminant par une amulette en forme de cœur solaire.",
        "era": "Late Period",
        "category": "Statues",
        "hall": "Royal Mummies Hall",
        "image_url": "/assets/exhibits/falcon_statuette.jpg",
        "x": 5.00, "y": -2.01,                  # ✓ verified walkable (re-used)
        "verified": True,
    },

    # ─── 4. Statue of the Scribe Mitri ───────────────────────────────
    {
        "title_en": "Statue of the Scribe Mitri",
        "title_ar": "تمثال الكاتب متري",
        "title_fr": "Statue du scribe Mitri",
        "short_en": "A painted wooden Dynasty 5 official, captured mid-thought with inlaid stone eyes.",
        "short_ar": "مسؤول من الأسرة 5 منحوت من الخشب المصقول، يظهر متأملاً بعيون من حجر مرصع.",
        "short_fr": "Un haut fonctionnaire de la 5e dynastie en bois peint, saisi en pleine réflexion, aux yeux incrustés de pierre.",
        "full_en": "Mitri was a high-ranking Dynasty 5 official whose titles included 'Nome Administrator', 'Priest of the goddess Ma'at', and 'Overseer of Scribes'. The painted wooden statue shows him in the traditional scribal pose — legs crossed, a partially unrolled papyrus on his lap, wearing a short kilt and a broad collar. His thoughtful expression is framed by short hair, and his magnetic eyes are made of inlaid stone — a technique that gives the statue an uncanny living presence over four thousand years later.",
        "full_ar": "كان متري من كبار المسؤولين في الأسرة الخامسة، ومن ألقابه 'مدير الإقليم' و'كاهن الإلهة ماعت' و'مشرف الكتبة'. يصوره التمثال الخشبي الملون في وضعية الكاتب التقليدية — متربعاً على الأرض، مع لفافة بردي مفتوحة جزئياً على حجره، يرتدي مئزراً قصيراً وقلادة عريضة. عيناه الجذابتان مصنوعتان من حجر مرصع.",
        "full_fr": "Mitri était un haut fonctionnaire de la 5e dynastie dont les titres comprenaient 'Administrateur du Nome', 'Prêtre de la déesse Maât' et 'Surveillant des scribes'. La statue en bois peint le représente dans la pose traditionnelle du scribe — jambes croisées, un papyrus partiellement déroulé sur les genoux, vêtu d'un pagne court et d'un large collier. Ses yeux magnétiques sont faits de pierre incrustée.",
        "era": "Old Kingdom",
        "category": "Statues",
        "hall": "Grand Atrium",
        "image_url": "/assets/exhibits/scribe_mitri.jpg",
        "x": -7.00, "y": -2.00,                 # ✎ guessed — verify on Ubuntu
        "verified": False,
    },

    # ─── 5. Seated Statue of Thutmose III ────────────────────────────
    {
        "title_en": "Seated Statue of Thutmose III",
        "title_ar": "تمثال جالس لتحتمس الثالث",
        "title_fr": "Statue assise de Thoutmôsis III",
        "short_en": "Granite portrait of the warrior pharaoh who built Egypt's largest empire.",
        "short_ar": "صورة جرانيتية للفرعون المحارب الذي بنى أكبر إمبراطورية لمصر.",
        "short_fr": "Portrait en granit du pharaon guerrier qui a bâti le plus grand empire d'Égypte.",
        "full_en": "Discovered at Karnak in 1859, this seated granite statue depicts the great warrior pharaoh Thutmose III on his throne. He wears the iconic nemes headcloth and the shendyt royal kilt, with hands placed palms-down on his knees in the classic regnal pose. Vertical inscriptions on the sides of the throne preserve his name and royal titles. Thutmose III is remembered for leading 17 military campaigns and expanding Egypt's empire to its greatest extent — earning him the title 'the Napoleon of Egypt'.",
        "full_ar": "اكتُشف هذا التمثال الجرانيتي الجالس في الكرنك عام 1859، ويصور الفرعون المحارب العظيم تحتمس الثالث على عرشه. يرتدي غطاء الرأس النمس الأيقوني والمئزر الملكي الشنديت، ويداه موضوعتان على ركبتيه براحتيهما لأسفل في الوضعية الملكية الكلاسيكية. تحفظ النقوش العمودية على جانبي العرش اسمه وألقابه الملكية. يُذكر تحتمس الثالث بقيادته 17 حملة عسكرية وتوسعة إمبراطورية مصر إلى أقصى حد لها.",
        "full_fr": "Découverte à Karnak en 1859, cette statue assise en granit représente le grand pharaon guerrier Thoutmôsis III sur son trône. Il porte la coiffe némès emblématique et le pagne royal shendyt, les mains posées paumes vers le bas sur les genoux dans la pose régnante classique. Des inscriptions verticales sur les côtés du trône conservent son nom et ses titres royaux. Thoutmôsis III est connu pour avoir mené 17 campagnes militaires et avoir étendu l'empire d'Égypte à son apogée.",
        "era": "New Kingdom",
        "category": "Statues",
        "hall": "Grand Atrium",
        "image_url": "/assets/exhibits/thutmose_iii.jpg",
        "x": 8.00, "y": 2.00,                   # ✎ guessed — verify on Ubuntu
        "verified": False,
    },

    # ─── 6. Head of King Amenhotep III ───────────────────────────────
    {
        "title_en": "Head of King Amenhotep III",
        "title_ar": "رأس الملك أمنحتب الثالث",
        "title_fr": "Tête du roi Amenhotep III",
        "short_en": "Fired-clay portrait whose elongated almond eyes foreshadow Amarna art.",
        "short_ar": "صورة من الطين المحروق بعيون لوزية ممدودة تنبئ بفن العمارنة.",
        "short_fr": "Portrait en argile cuite dont les yeux en amande allongés annoncent l'art amarnien.",
        "full_en": "This fired clay head from the Karnak Cache (CK 663) depicts King Amenhotep III near the end of his reign. He wears the khepresh — the blue ceremonial war crown — with a royal uraeus snake rearing protectively from his forehead. The distinctive large almond-shaped eyes would later become a defining feature of the radical Amarna art style introduced under his son Akhenaten. Amenhotep III's 38-year reign marked the artistic and diplomatic peak of the 18th Dynasty.",
        "full_ar": "يصور هذا الرأس المصنوع من الطين المحروق من خبيئة الكرنك (CK 663) الملك أمنحتب الثالث قرب نهاية عهده. يرتدي الخبرش — التاج الحربي الاحتفالي الأزرق — مع ثعبان الكوبرا الملكي ينتصب بحماية من جبهته. ستصبح العيون اللوزية الكبيرة المميزة لاحقاً سمة محددة لأسلوب فن العمارنة الجذري الذي أُدخل في عهد ابنه أخناتون. حدد عهد أمنحتب الثالث الذي استمر 38 عاماً ذروة فنية ودبلوماسية للأسرة 18.",
        "full_fr": "Cette tête en argile cuite provenant de la Cachette de Karnak (CK 663) représente le roi Amenhotep III vers la fin de son règne. Il porte le khepresh — la couronne de guerre cérémonielle bleue — avec un serpent uraeus royal se dressant protectivement sur son front. Les grands yeux en forme d'amande distinctifs deviendraient plus tard une caractéristique déterminante du style artistique radical amarnien introduit sous son fils Akhenaton. Le règne de 38 ans d'Amenhotep III a marqué le sommet artistique et diplomatique de la 18e dynastie.",
        "era": "New Kingdom",
        "category": "Statues",
        "hall": "Tutankhamun Gallery",
        "image_url": "/assets/exhibits/amenhotep_iii.jpg",
        "x": -4.00, "y": -5.00,                 # ✎ guessed — verify on Ubuntu
        "verified": False,
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
        # Clear event/log tables that would block exhibit/tour cleanup.
        # These are runtime tables (nav requests, tour runs, tour stops);
        # no master data lives here, so it's safe to wipe.
        db.execute(text("DELETE FROM navigation_requests"))
        db.execute(text("DELETE FROM tour_stops"))
        db.execute(text("DELETE FROM tour_runs"))
        db.flush()

        # Drop any legacy exhibits that aren't in our final list
        final_titles = {e["title_en"] for e in EXHIBITS}
        legacy = db.query(Exhibit).filter(~Exhibit.title_en.in_(final_titles)).all()
        for old in legacy:
            print(f"  [-] Removing legacy: {old.title_en}")
            db.delete(old)
        db.flush()

        # Upsert the 6 final exhibits
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
            row.short_description_en, row.short_description_ar, row.short_description_fr = ex["short_en"], ex["short_ar"], ex["short_fr"]
            row.full_description_en, row.full_description_ar, row.full_description_fr = ex["full_en"], ex["full_ar"], ex["full_fr"]
            row.era = ex["era"]
            row.category_id = category.id if category else None
            row.hall_id = hall.id if hall else None
            row.image_url = ex["image_url"]
            row.x_position = float(ex["x"])
            row.y_position = float(ex["y"])

            tag = "✓" if ex["verified"] else "?"
            print(f"  {action} {ex['title_en']:48s}  ({ex['x']:+5.2f}, {ex['y']:+5.2f}) {tag}")

        db.commit()
        print()
        print(f"Done. {len(legacy)} legacy removed, {added} added, {updated} updated.")
        print(f"Total exhibits in DB: {db.query(Exhibit).count()}")
        print()
        print("? = guessed coordinates — verify on Ubuntu with RViz 'Publish Point' then re-run.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
