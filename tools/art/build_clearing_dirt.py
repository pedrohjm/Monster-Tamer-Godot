"""Bake the painted clearing into the dirt brush, preserving the lake shoreline."""
from pathlib import Path

import numpy as np
from PIL import Image

from build_mini_mountain_atlas import join
from build_mountain_dualgrid import T, loop_strip, sample

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "art/source/dirt_clearing_reference.webp"
OUT = ROOT / "art/tiles"
OVERLAP = 16


def clearing_material(ref):
    # Keep the center of the illustration intact. Extend it with three runs
    # of soil so stones and little shoots can straddle any tile boundary.
    main = sample(ref, (170, 47, 458, 385), (176, 208))
    boxes = [(321, 247, 506, 379), (68, 169, 253, 277), (410, 166, 595, 271)]
    runs = [sample(ref, box, (112, 80)).swapaxes(0, 1) for box in boxes]
    side = join(join(runs[0], runs[1], OVERLAP), runs[2], OVERLAP)
    # Stagger the side run so prominent stones do not form horizontal pairs.
    side = np.roll(loop_strip(side, OVERLAP).swapaxes(0, 1), 67, axis=0)
    side = np.concatenate([side[-OVERLAP:], side])
    soil = loop_strip(join(main, side, OVERLAP), OVERLAP)
    return loop_strip(soil.swapaxes(0, 1), OVERLAP).swapaxes(0, 1)


def build():
    with Image.open(REFERENCE) as ref:
        soil = clearing_material(ref.convert("RGBA"))
    # The existing alpha masks also define the shape of the water's edge.
    with Image.open(OUT / "dirt.png") as base:
        shoreline = np.asarray(base.convert("RGBA"))[..., 3]
    height, width = soil.shape[:2]
    atlas = np.zeros((4*height, 4*width, 4), dtype=np.uint8)
    for y in range(0, height, T):
        for x in range(0, width, T):
            tile = soil[y:y+T, x:x+T]
            block = atlas[4*y:4*(y+T), 4*x:4*(x+T)]
            block[:] = np.tile(tile, (4, 4, 1))
            block[..., 3] = shoreline
            block[shoreline == 0] = 0
    Image.fromarray(atlas).save(OUT / "clearing_dirt.png")
    # Keep source 1 at the eight existing manual palette coordinates.
    Image.fromarray(soil[:T, :8*T]).save(OUT / "clearing_dirt_variants.png")


if __name__ == "__main__":
    build()
