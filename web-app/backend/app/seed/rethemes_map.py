"""
Convert simulation/maps/map.pgm into a themed museum_map.png for the web app.

Run after the simulation team updates their map:
    python -m app.seed.rethemes_map
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pathlib import Path

try:
    from PIL import Image, ImageFilter
    import numpy as np
except ImportError:
    print("Install Pillow + numpy first:  pip install Pillow numpy")
    sys.exit(1)


SRC = Path(__file__).resolve().parent.parent.parent.parent.parent / "simulation" / "maps" / "map.pgm"
DST_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "public" / "assets"
DST = DST_DIR / "museum_map.png"

# Theme — same gold + navy palette as the rest of the app
FLOOR  = (26, 34, 53, 255)
WALL   = (201, 168, 76, 255)
EDGE   = (212, 175, 55, 200)


def main() -> None:
    if not SRC.exists():
        print(f"Map source not found: {SRC}")
        print("(Pull the simulation/maps/map.pgm before running this.)")
        return

    DST_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.open(SRC).convert("L")
    w, h = img.size
    print(f"Source PGM: {w}x{h} pixels")

    arr = np.array(img, dtype=np.uint8)
    out = np.zeros((h, w, 4), dtype=np.uint8)

    free = arr >= 240
    walls = arr <= 80
    mid = ~free & ~walls & (arr > 0)

    out[free] = FLOOR
    out[walls] = WALL

    if mid.any():
        t = (255 - arr[mid]) / 255.0
        fl = np.array(FLOOR, dtype=np.float32)
        wl = np.array(WALL, dtype=np.float32)
        out[mid] = ((1 - t[..., None]) * fl + t[..., None] * wl).astype(np.uint8)

    # Soft halo around walls
    wall_only = Image.fromarray((walls * 255).astype(np.uint8))
    edges = wall_only.filter(ImageFilter.MaxFilter(3))
    edge_arr = np.array(edges) > 0
    halo = edge_arr & ~walls
    out[halo] = (*EDGE[:3], 200)

    Image.fromarray(out, mode="RGBA").save(DST, "PNG", optimize=True)
    print(f"Saved: {DST}  ({DST.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
