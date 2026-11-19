"""Bake the continuous grass meadow and its 16 dual-grid transitions at each map phase."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from build_clearing_dirt import REFERENCE as CLEARING
from build_mountain_dualgrid import ATLAS_BY_MASK, REFERENCE, T, distance_field, loop_strip, painted_turfs, sample

OUT = Path(__file__).resolve().parents[2] / "art" / "tiles"
COLS, ROWS = 6, 4


def floor_swatch(ref):
    # The summit tiles already share a seamless perimeter. Use them at their
    # original resolution and keep the same layout on paths and full ground.
    turfs = painted_turfs(ref)
    rng = np.random.default_rng(470)
    tiles = []
    while len(tiles) < ROWS * COLS:
        tiles.extend(turfs[i] for i in rng.permutation(len(turfs)))
    rows = [np.concatenate(tiles[i:i+COLS], axis=1) for i in range(0, ROWS*COLS, COLS)]
    return np.concatenate(rows, axis=0)


def bank_sprigs(height, width):
    """Paint little fans at map coordinates so a clump can cross a tile edge."""
    rng = np.random.default_rng(231)
    meadow = np.zeros((height, width), np.uint8)
    for y in range(0, height, 8):
        for x in range(0, width, 8):
            if rng.random() < 0.25:
                continue
            sprig = Image.new("L", (9, 7))
            pen = ImageDraw.Draw(sprig)
            for tip_x in (rng.integers(0, 3), rng.integers(3, 6), rng.integers(6, 9)):
                tip_y = int(rng.integers(0, 4))
                elbow = ((4 + int(tip_x)) // 2, tip_y + 1)
                pen.line([(4, 6), elbow, (int(tip_x), tip_y)], fill=85)
                pen.line([elbow, (int(tip_x), tip_y)], fill=int(rng.integers(145, 235)))
            ys = (y + rng.integers(0, 8) + np.arange(7)) % height
            xs = (x + rng.integers(0, 8) + np.arange(9)) % width
            region = np.ix_(ys, xs)
            meadow[region] = np.maximum(meadow[region], np.asarray(sprig))
    return meadow.astype(float)


def painted_sprigs():
    # Separate the upright grass blades from their original brown soil before
    # downsampling so translucent tips can also overlap the green side of a bank.
    boxes = [(517, 109, 597, 169), (112, 322, 180, 378), (491, 317, 563, 374),
             (347, 209, 404, 254)]
    sizes = [(23, 17), (17, 14), (21, 16), (15, 12)]
    sprites = []
    with Image.open(CLEARING) as reference:
        for box, size in zip(boxes, sizes):
            sprig = reference.crop(box).convert("RGBA")
            rgb = np.asarray(sprig, dtype=float)
            y, x = np.mgrid[:sprig.height, :sprig.width] + 0.5
            radius = ((x/sprig.width-0.5)/0.50)**2 + ((y/sprig.height-0.59)/0.45)**2
            silhouette = np.clip((1-radius)*3, 0, 1)
            green = rgb[..., 1]
            blade = np.clip((green-rgb[..., 0]+18)/30, 0, 1) * np.clip((green-56)/70, 0, 1)
            alpha = silhouette*blade
            sprig.putalpha(Image.fromarray(np.rint(255*alpha).astype(np.uint8)))
            sprites.append(sprig.resize(size, Image.Resampling.LANCZOS))
    return sprites


def bank_stamps(width, height, sprites):
    rng = np.random.default_rng(362)
    by_cell = {(x, y): [] for y in range(ROWS) for x in range(COLS)}
    for y in range(0, height, 8):
        for x in range(0, width, 8):
            ax, ay = x + int(rng.integers(8)), y + int(rng.integers(8))
            sprig = sprites[int(rng.integers(len(sprites)))]
            left, top = ax - sprig.width//2, ay - round(0.82*sprig.height)
            for cy in range(top//T, (top+sprig.height-1)//T + 1):
                for cx in range(left//T, (left+sprig.width-1)//T + 1):
                    by_cell[cx % COLS, cy % ROWS].append(
                        (ax-cx*T, ay-cy*T, left-cx*T, top-cy*T, sprig))
    return by_cell


def draw_bank(tile, mask, depth, stamps, sway_x, sway_y, cx, cy):
    result = Image.fromarray(tile)
    for ax, ay, left, top, sprig in stamps:
        crosses_x = left <= 0 or left + sprig.width >= T
        crosses_y = top <= 0 or top + sprig.height >= T
        if crosses_x and crosses_y:
            continue
        # A tuft crossing a tile boundary belongs to both tiles. Both select
        # it from their two shared corners, including at the map repeat.
        wx, wy = (cx*T+ax) % sway_x.shape[1], (cy*T+ay) % sway_x.shape[0]
        if crosses_x or crosses_y:
            if crosses_x:
                first, last = (8, 2) if left <= 0 else (4, 1)
                across = ay+0.5+sway_y[wy, wx]-T/2
            else:
                first, last = (8, 4) if top <= 0 else (2, 1)
                across = ax+0.5+sway_x[wy, wx]-T/2
            if bool(mask & first) == bool(mask & last):
                continue
            root_depth = across if mask & last else -across
        else:
            root_depth = depth[ay, ax]
        if 1.0 <= root_depth <= 8.0:
            result.alpha_composite(sprig, (left, top))
    return np.asarray(result)


def build():
    reference = Image.open(REFERENCE).convert("RGBA").resize((2048, 752), Image.Resampling.LANCZOS)
    meadow = floor_swatch(reference)
    height, width = meadow.shape[:2]
    y, x = np.mgrid[:height, :width] + 0.5
    # Perturb the common contour in map space. At a shared cell edge both
    # masks sample the same offset, right down to the individual blade tips.
    u, v = x*2*np.pi/width, y*2*np.pi/height
    sway_x = 1.45*np.sin(5*v + 0.8*np.sin(2*u)) + 0.8*np.sin(11*v + u)
    sway_y = 1.60*np.sin(7*u + 0.9*np.sin(3*v)) + 0.65*np.sin(15*u - v)
    padded = np.pad(meadow[..., 1], 4, mode="wrap")
    green = Image.fromarray(padded)
    light = np.asarray(green.filter(ImageFilter.GaussianBlur(0.85)), dtype=float)[4:-4, 4:-4]
    local = np.asarray(green.filter(ImageFilter.GaussianBlur(2.0)))[4:-4, 4:-4]
    blades = np.clip((light-local)/16, -1, 1.6)
    sprigs = bank_sprigs(height, width)
    stamps = bank_stamps(width, height, painted_sprigs())

    # The lawn meets soil with short, lit blades and a shallow contact shadow.
    # The larger tuft texture is confined to the inner few pixels of each bank.
    lip = loop_strip(sample(reference, (196, 433, 664, 516), (140, 24)), 12)
    atlas = np.zeros((4*height, 4*width, 4), np.uint8)
    for cy in range(ROWS):
        for cx in range(COLS):
            window = np.s_[cy*T:(cy+1)*T, cx*T:(cx+1)*T]
            px, py = x[window], y[window]
            for mask, (ax, ay) in enumerate(ATLAS_BY_MASK):
                depth = distance_field(mask, px % T+sway_x[window], py % T+sway_y[window])
                depth += blades[window]*0.32
                tile = meadow[window].copy()
                edge = np.clip(1-np.abs(depth-1.2)/5.0, 0, 1)
                nx = np.abs(np.gradient(depth, axis=1))
                ny = np.abs(np.gradient(depth, axis=0))
                along = np.where(nx > ny, py, px).astype(int) % lip.shape[1]
                row = np.clip(18 - np.floor(depth*1.6), 0, len(lip)-1).astype(int)
                leaves = lip[row, along, :3]
                strength = (0.65 * edge)[..., None]
                color = tile[..., :3]*(1-strength) + leaves*strength
                ink = sprigs[window]
                bank = np.clip(1-np.abs(depth-3)/6, 0, 1) * (ink > 0)
                tint = ((ink-112)/130 * bank)[..., None]
                color += tint * np.array([39, 28, 6])
                shade = 1 - 0.23*np.clip(1-np.abs(depth+0.25)/1.5, 0, 1)
                tile[..., :3] = np.clip(np.rint(color * shade[..., None]), 0, 255)
                tile[..., 3] = np.rint(255*np.clip(depth+1.15, 0, 1))
                tile[tile[..., 3] == 0] = 0
                if mask not in (0, 15):
                    tile = draw_bank(tile, mask, depth, stamps[cx, cy], sway_x, sway_y, cx, cy)
                left, top = (4*cx+ax)*T, (4*cy+ay)*T
                atlas[top:top+T, left:left+T] = tile
    Image.fromarray(atlas).save(OUT / "meadow_grass.png")
    # Source 1 remains usable by maps painted manually with any of the ten
    # former variant coordinates. The grass brush uses the complete meadow.
    full_tiles = [meadow[r*T:(r+1)*T, c*T:(c+1)*T]
                  for r in range(ROWS) for c in range(COLS)]
    Image.fromarray(np.concatenate(full_tiles[:10], axis=1)).save(OUT / "meadow_grass_variants.png")


if __name__ == "__main__":
    build()
