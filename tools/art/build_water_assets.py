"""Build the animated lake, its submerged bed and the land/water contact tiles."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter

from build_mountain_dualgrid import ATLAS_BY_MASK, T, loop_strip, sample

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art/tiles"
REFERENCE = ROOT / "art/source/turquoise_lake_reference.webp"
WIDTH, HEIGHT = 6*T, 5*T
FRAMES = 16
OVERLAP = 16


def swatch(ref, box, size):
    # Coordinates in the 716-pixel-wide study. Sample from the larger source.
    scale = ref.width / 716
    return sample(ref, tuple(round(p*scale) for p in box), size)[..., :3]


def open_water(ref):
    # Keep the original painted caustics continuous inside long strips.
    a = swatch(ref, (193, 47, 518, 158), (208, 72))
    b = blend_runs(swatch(ref, (399, 209, 637, 311), (152, 76)),
                   swatch(ref, (89, 216, 201, 308), (72, 76)))
    c = blend_runs(swatch(ref, (240, 67, 488, 153), (144, 60)),
                   swatch(ref, (406, 246, 534, 339), (80, 60)))
    a, b, c = [closed_run(row).swapaxes(0, 1) for row in (a, b, c)]
    surface = closed_run(blend_runs(blend_runs(a, b), c)).swapaxes(0, 1)
    # Reserve the olive glints of the submerged rocks for the shallow bed.
    green = np.clip((surface[..., 1]-surface[..., 2]-4)/24, 0, 1)
    surface[..., 0] *= 1-0.35*green
    surface[..., 1] *= 1-0.19*green
    surface[..., 2] += 6*green
    return surface


def blend_runs(left, right):
    weight = (0.5-0.5*np.cos(np.linspace(0, np.pi, OVERLAP)))[None, :, None]
    transition = left[:, -OVERLAP:]*(1-weight) + right[:, :OVERLAP]*weight
    return np.concatenate([left[:, :-OVERLAP], transition, right[:, OVERLAP:]], axis=1)


def closed_run(run):
    return blend_runs(run, run[:, :OVERLAP])[:, OVERLAP:]


def wrapped_sample(pixels, x, y):
    h, w = pixels.shape[:2]
    col, row = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x-col)[..., None], (y-row)[..., None]
    a = pixels[row % h, col % w]*(1-fx) + pixels[row % h, (col+1) % w]*fx
    b = pixels[(row+1) % h, col % w]*(1-fx) + pixels[(row+1) % h, (col+1) % w]*fx
    return a*(1-fy) + b*fy


def water_frame(surface, t):
    y, x = np.indices(surface.shape[:2])
    u, v = 2*np.pi*x/WIDTH, 2*np.pi*y/HEIGHT
    dx = 2.6*np.sin(2*v+t+0.65*np.sin(u)) + 1.1*np.cos(3*u-v-t)
    dy = 1.6*np.cos(2*u-t+0.6*np.sin(v)) + 0.75*np.sin(u+3*v+t)
    rgb = wrapped_sample(surface, x+dx, y+dy)
    # Light catches the crests in succession while the darker bed reads as still.
    crest = np.clip((rgb[..., 1]-102)/98, 0, 1)
    glint = crest*(0.5+0.5*np.cos(3*u+2*v-t))**2
    rgb += glint[..., None]*np.array([20, 22, 23])
    return np.uint8(np.clip(np.rint(rgb), 0, 255))


def bed_material(ref):
    boxes = [(74, 148, 172, 195), (15, 246, 91, 284), (543, 151, 632, 207),
             (403, 172, 458, 228), (540, 317, 597, 345), (44, 339, 108, 370)]
    rocks = [swatch(ref, b, (round((b[2]-b[0])*0.72), round((b[3]-b[1])*0.72)))
             for b in boxes]
    y, x = np.indices((HEIGHT, WIDTH))
    u, v = 2*np.pi*x/WIDTH, 2*np.pi*y/HEIGHT
    tone = np.sin(u+v)*3 + np.cos(3*u-2*v)*4
    bed = np.array([18, 127, 124]) + tone[..., None]
    density = np.full((HEIGHT, WIDTH), 0.22)
    rng = np.random.default_rng(395)
    for row in range(4):
        for col in range(4):
            patch = rocks[(row+3*col+int(rng.integers(3))) % len(rocks)]
            h, w = patch.shape[:2]
            py, px = np.mgrid[:h, :w]+0.5
            radius = ((px-w/2)/(w/2))**2 + ((py-h/2)/(h/2))**2
            blend = np.clip(1.9*(1-radius), 0, 1)
            oy = row*40 + int(rng.integers(-12, 13))
            ox = col*48 + int(rng.integers(-16, 17))
            area = np.ix_((oy+np.arange(h)) % HEIGHT, (ox+np.arange(w)) % WIDTH)
            lit_rock = patch.astype(float) + [5, 8, 1]
            bed[area] = bed[area]*(1-blend[..., None]) + lit_rock*blend[..., None]
            density[area] = np.maximum(density[area], 0.22+0.66*blend)
    return np.uint8(np.clip(np.rint(bed), 0, 255)), density


def shallows_atlas(ref):
    bed, density = bed_material(ref)
    atlas = np.zeros((4*HEIGHT, 4*WIDTH, 4), np.uint8)
    y, x = (np.indices((T, T))+0.5)/T
    # Bilinear corner weights interpolate depth across shared tile boundaries.
    weights = [(1-x)*(1-y), x*(1-y), (1-x)*y, x*y]
    for mask, (ax, ay) in enumerate(ATLAS_BY_MASK):
        depth = sum(w*bool(mask & bit) for w, bit in zip(weights, (8, 4, 2, 1)))
        fade = depth*depth*(3-2*depth)
        for top in range(0, HEIGHT, T):
            for left in range(0, WIDTH, T):
                section = np.s_[top:top+T, left:left+T]
                oy, ox = 4*top+ay*T, 4*left+ax*T
                tile = atlas[oy:oy+T, ox:ox+T]
                tile[..., :3] = bed[section]
                tile[..., 3] = np.rint(255*density[section]*fade)
                tile[tile[..., 3] == 0] = 0
    return atlas


def stone_strip(ref):
    # Trace the foot of the painted bank in each column. This keeps foam and
    # grass out of the rock material when bending it around different shores.
    strip = swatch(ref, (183, 10, 530, 44), (272, 30))
    r, g, b = strip.astype(float).transpose(2, 0, 1)
    rock = (r > 1.08*g) & (g > b+6)
    row = np.arange(len(strip))[:, None]
    bottom = np.max(np.where(rock, row, 0), axis=0)
    top = np.maximum(bottom-10, 0)
    rows = np.rint(top+(bottom-top)*np.linspace(0, 1, 8)[:, None]).astype(int)
    return loop_strip(strip[rows, np.arange(strip.shape[1])], OVERLAP)


def shoreline_atlas(ref):
    masks = np.asarray(Image.open(OUT / "dirt.png").convert("RGBA"))[..., 3]
    stone = stone_strip(ref)
    cols, rows = 4, 3
    atlas = np.zeros((4*rows*T, 4*cols*T, 4), np.uint8)
    for mask, (ax, ay) in enumerate(ATLAS_BY_MASK):
        if mask in (0, 15):
            continue
        land = masks[ay*T:(ay+1)*T, ax*T:(ax+1)*T] > 0
        # Extend the mask before measuring distances so tile edges are never
        # interpreted as banks. Six pixels of projection give the south face height.
        pad = 12
        land = np.pad(land, pad, mode="edge")
        wall = np.zeros(land.shape, int)
        for step in range(6, 0, -1):
            wall[step:] = np.where(land[:-step], step, wall[step:])
        solid = land | (gaussian_filter((land | (wall > 0)).astype(float), 1.15) >= 0.45)
        core = np.s_[pad:pad+T, pad:pad+T]
        distance = distance_transform_edt(~solid)[core]
        face = (solid & ~land)[core]
        elevation = np.where(wall[core] > 0, wall[core], 6)
        y, x = np.indices((T, T))
        for cy in range(rows):
            for cx in range(cols):
                wx, wy = cx*T+x, cy*T+y
                u, v = 2*np.pi*wx/(cols*T), 2*np.pi*wy/(rows*T)
                wave = 0.5+0.5*np.sin(11*u+5*v+1.4*np.sin(3*u-2*v))
                lace = 0.5+0.5*np.cos(17*u-9*v)
                tile = np.zeros((T,T,4), np.uint8)
                water = distance > 0
                # A translucent shadow, then a broken second ripple outside a
                # narrow, continuous pale-turquoise contact line.
                tile[..., :3] = [10, 70, 78]
                alpha = np.where(water, 0.40*np.exp(-distance/3.1), 0)
                foam = np.clip(1.6+0.95*wave-distance, 0, 1)
                second = np.maximum(1-np.abs(distance-(3.0+1.4*wave)), 0)*lace**2*0.38
                foam = np.where(water, np.maximum(foam, second), 0)
                opacity = foam + alpha*(1-foam)
                white = np.array([125, 205, 199]) + wave[..., None]*np.array([80, 40, 42])
                rgb = (white*foam[..., None]+tile[..., :3]*(alpha*(1-foam))[..., None])
                tile[..., :3] = np.rint(rgb/np.maximum(opacity, 0.001)[..., None])
                tile[..., 3] = np.rint(255*opacity)
                # The strip repeats exactly across the map's four-column phase.
                along = (2*wx + 8*wy) % stone.shape[1]
                # Along a front-facing wall the same fissure continues down the face.
                along = (along-8*elevation) % stone.shape[1]
                tile[face, :3] = stone[np.clip(elevation[face], 0, 7), along[face]]
                tile[face, 3] = 255
                oy, ox = (4*cy+ay)*T, (4*cx+ax)*T
                atlas[oy:oy+T, ox:ox+T] = tile
    return atlas


def build():
    with Image.open(REFERENCE) as image:
        ref = image.convert("RGB")
        surface = open_water(ref)
        frames = [water_frame(surface, i*2*np.pi/FRAMES) for i in range(FRAMES)]
        Image.fromarray(np.concatenate(frames, axis=1)).save(OUT / "water.png")
        Image.fromarray(shallows_atlas(ref)).save(OUT / "water_shallows.png")
        Image.fromarray(shoreline_atlas(ref)).save(OUT / "dirt_shore.png")


if __name__ == "__main__":
    build()
