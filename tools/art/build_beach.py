"""Build a periodic sand surface and a separate, low surf line for the water brush."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d, median_filter, uniform_filter

from build_mini_mountain_atlas import join
from build_mountain_dualgrid import ATLAS_BY_MASK, T, distance_field, loop_strip, sample

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art/tiles"
COLS, ROWS, OVERLAP = 8, 6, 8


def closed_quilt(pieces):
    strip = pieces[0]
    for piece in pieces[1:]:
        strip = join(strip, piece, OVERLAP)
    return loop_strip(strip, OVERLAP)


def dry_sand(ref):
    r, g, b = np.asarray(ref, dtype=float)[..., :3].transpose(2, 0, 1)
    sand = (r > 171) & (r-g > 4) & (g-b > 21) & (b > 65) & (g > 129)
    ys, xs = np.where(uniform_filter(sand.astype(float), 40, mode="constant") > 0.995)
    rng = np.random.default_rng(810)
    bands = []
    for _ in range(2*ROWS):
        pieces = []
        for k in rng.choice(len(xs), 2*COLS, replace=False):
            x, y = int(xs[k]), int(ys[k])
            pieces.append(sample(ref, (x-20,y-20,x+20,y+20), (T+OVERLAP,T+OVERLAP)))
        bands.append(closed_quilt(pieces).swapaxes(0, 1))
    quilt = closed_quilt(bands).swapaxes(0, 1)
    padded = np.pad(quilt, ((6,6),(6,6),(0,0)), mode="wrap")
    scaled = Image.fromarray(padded).resize((COLS*T+6,ROWS*T+6),Image.Resampling.LANCZOS)
    material = np.array(scaled)[3:-3,3:-3].copy()
    # Give the occasional shell or star its own sand and contact shadow.
    for box, size, (x,y) in [
        ((105,521,165,574), (22,18), (74,47)),
        ((614,26,679,68), (23,15), (182,38)),
        ((1074,46,1115,77), (13,10), (221,167)),
    ]:
        detail = sample(ref, box, size)
        h,w = detail.shape[:2]
        py,px = np.mgrid[:h,:w]+0.5
        radius = ((px-w/2)/(w/2))**2+((py-h/2)/(h/2))**2
        alpha = np.clip((1-radius)*3,0,1)[...,None]
        area = material[y:y+h,x:x+w]
        area[:] = np.rint(area*(1-alpha)+detail*alpha)
    return material


def surf_strip(ref):
    # Follow the first pale breakers along the long northern beach. Keep their
    # actual branching highlights and the amber sand visible through the wash.
    run = np.asarray(ref)[19:163,530:1070]
    r,g,b = run[...,:3].astype(float).transpose(2,0,1)
    water = (b > 110) & (g-r > -12) & (b-r > -40)
    water[:48] = False
    shore_y = gaussian_filter1d(median_filter(water.argmax(axis=0), size=9).astype(float), 2)
    row = np.rint(shore_y[None,:]+np.linspace(-11,34,30)[:,None]).astype(int)
    strip = Image.fromarray(run[np.clip(row,0,len(run)-1),np.arange(run.shape[1])])
    return loop_strip(np.array(strip.resize((272,30),Image.Resampling.LANCZOS)),16)


def build():
    with Image.open(ROOT / "art/source/beach_reference.webp") as image:
        ref = image.convert("RGBA")
        sand, surf = dry_sand(ref), surf_strip(ref)
    h,w = sand.shape[:2]
    body = np.zeros((h*4,w*4,4),np.uint8)
    bank = np.zeros_like(body)
    for top in range(0,h,T):
        for left in range(0,w,T):
            y,x = np.mgrid[:T,:T]+0.5
            u,v = (left+x)*2*np.pi/w, (top+y)*2*np.pi/h
            dx = 1.35*np.sin(5*v+np.sin(2*u))
            dy = 1.65*np.sin(6*u+np.sin(3*v))
            along = np.floor((u+v)/(2*np.pi)*surf.shape[1]).astype(int)%surf.shape[1]
            for mask,(ax,ay) in enumerate(ATLAS_BY_MASK):
                depth = distance_field(mask,x+dx,y+dy)
                tile = sand[top:top+T,left:left+T].copy()
                damp = np.clip((5-depth)/6,0,1)[...,None]
                tile[...,:3] = np.rint(tile[...,:3]*(1-damp*np.array([0.08,0.13,0.18])))
                tile[...,3] = np.rint(255*np.clip(depth+0.5,0,1))
                tile[tile[...,3]==0] = 0
                row = np.clip(np.rint(5-depth*1.40),0,len(surf)-1).astype(int)
                shore = surf[row,along].copy()
                fade = np.clip((15+depth)/9,0,1)
                shore[...,3] = np.rint(255*fade*fade*(3-2*fade))
                shore[(depth>1)|(shore[...,3]==0)] = 0
                oy,ox = 4*top+ay*T,4*left+ax*T
                body[oy:oy+T,ox:ox+T] = tile
                bank[oy:oy+T,ox:ox+T] = shore
    Image.fromarray(body).save(OUT/"beach_sand.png")
    Image.fromarray(bank).save(OUT/"beach_surf.png")


if __name__ == "__main__":
    build()
