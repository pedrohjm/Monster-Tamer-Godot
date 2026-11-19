"""Build the editable mountain brush. The 16 dual-grid masks share one rounded
outline for the grassy top and the textured cliff projected below it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_mini_mountain_atlas import join  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "art/source/mountain_meadow_reference.webp"
TOP_OUT = ROOT / "art/tiles/mountain_top.png"
VARIANTS_OUT = ROOT / "art/tiles/mountain_variants.png"
FACE_OUT = ROOT / "art/tiles/mountain_face.png"
T = 32
ROWS = 3
FACE_LIP = 30
RADIUS = 11
WALL_HEIGHT = 45
LEAN = 12
FACE_WIDTH = T * 2  # overhang into the adjacent cell

ATLAS_BY_MASK = [
    (0, 3), (1, 3), (0, 0), (3, 0), (0, 2), (1, 0), (2, 3), (1, 1),
    (3, 3), (0, 1), (3, 2), (2, 0), (1, 2), (2, 2), (3, 1), (2, 1),
]


def distance_field(mask, x, y):
    """Positive inside. Each quarter circle meets its neighboring straight tangentially."""
    if mask in (0, 15):
        return np.full_like(x, 64.0 if mask else -64.0)
    if mask in (3, 12):
        return (y - T/2) * (1 if mask == 3 else -1)
    if mask in (5, 10):
        return (x - T/2) * (1 if mask == 5 else -1)
    if mask.bit_count() == 3:
        return -distance_field(15 ^ mask, x, y)
    if mask in (6, 9):
        # Round the two empty corners so diagonal brush strokes share a grassy neck.
        empty = 15 ^ mask
        first = empty & -empty
        return -np.maximum(distance_field(first, x, y), distance_field(empty ^ first, x, y))
    # Signed distance to a quadrant with a circular fillet at its tip.
    dx = (x - T/2) * (1 if mask in (8, 2) else -1) + RADIUS
    dy = (y - T/2) * (1 if mask in (8, 4) else -1) + RADIUS
    return RADIUS - np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) - np.minimum(np.maximum(dx, dy), 0)


def sample(image, box, size):
    """Reduce the painted brushwork to native tile pixels before assembling the atlas."""
    patch = image.crop(box).resize(size, Image.Resampling.LANCZOS)
    return np.asarray(patch.filter(ImageFilter.UnsharpMask(radius=0.75, percent=95, threshold=3)))


def loop_strip(pixels, overlap):
    # Close the material through a least-cost seam; rolling moves that seam
    # away from the cell boundary. Every adjacent 32-pixel run shares its phase.
    return join(pixels, pixels[:, :overlap], overlap)[:, overlap:]


def painted_turfs(reference):
    # Interior patches of the meadow, including a few low rosettes. None
    # crosses a cliff, so the paint brush can use any swatch for a full cell.
    centers = [(413, 212), (270, 182), (418, 320), (505, 174), (338, 269),
               (570, 295), (257, 312), (612, 193), (705, 168), (1080, 235),
               (1168, 285), (1250, 176), (1510, 177)]
    repeat = sample(reference, (378, 140, 518, 280), (40, 40))
    repeat = loop_strip(loop_strip(repeat, 8).transpose(1, 0, 2), 8).transpose(1, 0, 2)
    y, x = np.indices((T,T))
    distance = np.minimum.reduce([x, y, T-1-x, T-1-y])
    weight = np.clip(distance / 4, 0, 1)[..., None]
    tiles = []
    for cx, cy in centers:
        patch = sample(reference, (cx-53, cy-53, cx+53, cy+53), (T, T))
        tiles.append(np.rint(repeat*(1-weight) + patch*weight).astype(np.uint8))
    return tiles


def side_grass(reference, y_start, y_end, x_top, x_bottom, direction):
    # Straighten just the lean of the painted edge, keeping each plant upright.
    # Row zero of the returned swatch touches the outside of the grassy shelf.
    source = np.asarray(reference)
    ys = np.arange(y_start, y_end)
    xs = np.rint(np.linspace(x_top, x_bottom, len(ys))).astype(int)
    strip = source[ys[:, None], xs[:, None] + direction*np.arange(84)]
    upright = sample(Image.fromarray(strip), (0, 0, 84, len(ys)), (24, 42))
    return loop_strip(upright.transpose(1, 0, 2), 10)


def crown_tips(north, lip):
    # Only keep illuminated brushstrokes which actually grow from the rim.
    # Disconnected highlights belong to the ground behind the reference.
    colors = north[:lip, :, :3].astype(int)
    light = (colors[..., 0] > 131) & (colors[..., 1] > 142)
    attached = np.ones(north.shape[1], bool)
    for row in reversed(range(lip)):
        attached = light[row] & (attached | np.roll(attached, 1) | np.roll(attached, -1))
        light[row] = attached
    return light


def corner_flowers(top, depth, flowers):
    h, w = flowers.shape[:2]
    y, x = np.indices(depth.shape)
    # Tuck this upright sprig just inside the turn; do not warp individual petals.
    distance = np.abs(depth-7) + 0.3*np.hypot(x-T/2, y-T/2)
    cy, cx = np.unravel_index(np.argmin(distance), distance.shape)
    x0 = int(np.clip(cx-w//2, 0, T-w))
    y0 = int(np.clip(cy-h//2, 0, T-h))
    py, px = np.indices((h, w))
    radius = ((px-(w-1)/2)/(w/2))**2 + ((py-(h-1)/2)/(h/2))**2
    blend = np.clip(2.4*(1-radius), 0, 1)[..., None]
    region = top[y0:y0+h, x0:x0+w]
    region[:] = np.rint(region*(1-blend)+flowers*blend).astype(np.uint8)


def render_piece(mask, turf, front, north, west, east, tips, flowers, variation):
    gy, gx = np.mgrid[-1:T+1, -1:T+1] + 0.5
    field = distance_field(mask, gx, gy)
    core = np.s_[1:-1, 1:-1]
    depth = field[core]
    normal_y, normal_x = np.gradient(-field)
    nx, ny = normal_x[core], normal_y[core]
    y, x = np.indices(depth.shape)
    phase = variation * T
    horizontal = (x + phase) % front.shape[1]
    # Adjacent columns share the same side-grass stitch when the rim turns.
    vertical = y % west.shape[1]
    inside = np.maximum(np.floor(depth).astype(int), 0)

    # Sample the actual painted lip: backlit foliage at the rear, upright
    # clumps at the sides, and overhanging blades where the wall faces south.
    front_leaf = front[np.maximum(FACE_LIP-inside, 0), horizontal]
    rear_leaf = north[np.minimum(len(tips)+inside, len(north)-1), horizontal]
    side_row = np.minimum(inside, len(west)-1)
    side_leaf = np.where((nx > 0)[..., None], east[side_row, vertical], west[side_row, vertical])
    cap = np.where((ny < 0)[..., None], rear_leaf, front_leaf)
    weight = np.clip((np.abs(ny)-np.abs(nx)+0.35)/0.7, 0, 1)[..., None]
    leaf = side_leaf*(1-weight) + cap*weight
    # A painted side sample may include a pixel of the cliff underneath.
    # Give that contact point a moss shadow on the top; keep warm gold petals.
    red, green, blue = leaf[..., 0], leaf[..., 1], leaf[..., 2]
    earth = (red > green+12) & (green < 136) & (green-blue < 55)
    leaf[earth, :3] = turf[earth, :3]*0.76
    # Leave the outer blades intact, then ease into the common turf before
    # the next full cell. Its first pixel must already look like the meadow.
    coverage = np.clip((T/2-1-depth)/9, 0, 1)[..., None]
    coverage = coverage*coverage*(3-2*coverage)
    top = np.rint(turf*(1-coverage)+leaf*coverage).astype(np.uint8)
    if mask.bit_count() in (1, 3) and (mask+variation) % 5 == 0:
        corner_flowers(top, depth, flowers[variation % len(flowers)])
    top[depth < 0] = 0

    wall = np.zeros((ROWS*T, FACE_WIDTH, 4), dtype=np.uint8)
    # Continue down the same painted strip to preserve hanging leaves,
    # their contact shadows, and the warm rock directly underneath them.
    u = (x - y + T//2 + phase) % front.shape[1]
    for z in range(WALL_HEIGHT, 0, -1):
        shift = round(LEAN*z/WALL_HEIGHT)
        step = shift - round(LEAN*(z-1)/WALL_HEIGHT)
        neighbor = field[2:, 1+step:1+step+T]
        by, bx = np.nonzero((depth >= 0) & (neighbor < 0))
        sy = FACE_LIP + round((len(front)-1-FACE_LIP)*z/WALL_HEIGHT)
        stone = front[sy, u[by, bx]].copy()
        shade = 1 - 0.22*np.clip(nx[by, bx], 0, 1)
        stone[:, :3] = np.rint(stone[:, :3]*shade[:, None])
        wall[by+z, bx+shift] = stone
    wall[:T, :T][depth >= 0] = 0
    tip_row = np.clip(len(tips)+np.floor(depth).astype(int), 0, len(tips)-1)
    protrudes = (ny < -0.65) & (depth < 0) & (depth >= -len(tips)) & tips[tip_row, horizontal]
    wall[:T, :T][protrudes] = north[tip_row[protrudes], horizontal[protrudes]]
    return top, wall


def clipped_faces(top, walls):
    """Bake only distinct cuts where another plateau covers a projected face."""
    silhouettes = [top[y*T:(y+1)*T, x*T:(x+1)*T, 3] != 0 for x,y in ATLAS_BY_MASK]
    lookup = []
    extras = []
    cuts = {}
    footprints = [np.any(group[..., 3] > 0, axis=0) for group in walls]
    # Twelve painted cells (three columns by four rows) cover all six
    # display cells reachable by a 12x45 pixel projection.
    for bits in range(1 << 12):
        def corners(x, y):
            i = y*3+x
            return sum(((bits >> (i+k)) & 1)*w for k,w in ((0,8),(1,4),(3,2),(4,1)))
        mask = corners(0, 0)
        hidden = np.zeros((ROWS*T, FACE_WIDTH), bool)
        for dy in range(3):
            for dx in range(2):
                hidden[dy*T:(dy+1)*T, dx*T:(dx+1)*T] = silhouettes[corners(dx,dy)]
        hidden &= footprints[mask]
        if not hidden.any():
            lookup.append(0)
            continue
        key = (mask, np.packbits(hidden).tobytes())
        if key not in cuts:
            group = walls[mask].copy()
            group[:, hidden] = 0
            extras.append((mask, group))
            cuts[key] = len(extras)
        lookup.append(cuts[key])
    return lookup, extras


def build() -> None:
    # The sampling coordinates are expressed in the attached illustration's
    # 2048-pixel-wide layout; its reduced source stays outside Godot imports.
    reference = Image.open(REFERENCE).convert("RGBA").resize((2048, 752), Image.Resampling.LANCZOS)
    front = loop_strip(sample(reference, (196, 402, 664, 659), (140, 77)), 12)
    north = loop_strip(sample(reference, (192, 34, 674, 144), (140, 33)), 12)
    tips = crown_tips(north, 6)
    flowers = [sample(reference, (646, 368, 706, 422), (18, 16)),
               sample(reference, (1634, 91, 1689, 134), (16, 13))]
    west = side_grass(reference, 204, 354, 24, 26, 1)
    east = side_grass(reference, 340, 475, 1923, 1945, -1)
    turfs = painted_turfs(reference)
    variations = front.shape[1] // T
    top = np.zeros((4*T, 4*T, 4), dtype=np.uint8)
    face_atlas = np.zeros((4*ROWS*T, 4*FACE_WIDTH*variations, 4), dtype=np.uint8)
    walls = []
    for mask, (ax, ay) in enumerate(ATLAS_BY_MASK):
        group = []
        for v in range(variations):
            surface, wall = render_piece(mask, turfs[v], front, north, west, east, tips, flowers, v)
            if v == 0:
                top[ay*T:(ay+1)*T, ax*T:(ax+1)*T] = surface
            group.append(wall.copy())
            if mask not in (0, 15):
                inside = surface[..., 3] > 0
                wall[:T, :T][inside] = surface[inside]
            ox, oy = (ax+4*v)*FACE_WIDTH, ay*ROWS*T
            face_atlas[oy:oy+ROWS*T, ox:ox+FACE_WIDTH] = wall
        walls.append(np.stack(group))
    lookup, extras = clipped_faces(top, walls)
    Image.fromarray(top).save(TOP_OUT)
    variants = np.concatenate(turfs[1:], axis=1)
    Image.fromarray(variants).save(VARIANTS_OUT)

    # Extra groups contain four variations; keep the original top cap for
    # each one while clipping only rock behind another painted cell.
    extra_atlas = np.zeros((((len(extras)+3)//4)*ROWS*T, face_atlas.shape[1], 4), np.uint8)
    for number, (mask, group) in enumerate(extras):
        ax, ay = ATLAS_BY_MASK[mask]
        for v, wall in enumerate(group):
            original = face_atlas[ay*ROWS*T:ay*ROWS*T+T, (ax+4*v)*FACE_WIDTH:(ax+4*v)*FACE_WIDTH+T]
            inside = top[ay*T:(ay+1)*T, ax*T:(ax+1)*T, 3] != 0
            wall[:T, :T][inside] = original[inside]
            ox = (4*(number%4)+v)*FACE_WIDTH
            oy = (number//4)*ROWS*T
            extra_atlas[oy:oy+ROWS*T, ox:ox+FACE_WIDTH] = wall
    Image.fromarray(np.concatenate((face_atlas, extra_atlas))).save(FACE_OUT)
    FACE_OUT.with_suffix(".json").write_text(json.dumps(lookup, separators=(",", ":"))+"\n")
    print("Distinct mountain overlaps:", len(extras))
    print(f"salvo em {TOP_OUT.relative_to(ROOT)}, {VARIANTS_OUT.relative_to(ROOT)} e "
          f"{FACE_OUT.relative_to(ROOT)} ({variations} paredões)")


if __name__ == "__main__":
    build()
