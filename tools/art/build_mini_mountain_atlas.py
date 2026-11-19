"""Build the Godot terrain atlas and the two stair patches from the original sheets."""
import argparse
import json
import shutil
from pathlib import Path
from build_mountain_stairs import build as build_stairs

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[2] / "art" / "tiles"
T = 32
TURF = np.array([77, 119, 53, 255], dtype=np.uint8)


def join(left, right, overlap=13):
    """Join two cliff runs along the least visible connected seam in their overlap."""
    a, b = left[:, -overlap:], right[:, :overlap]
    delta = a.astype(float) - b
    costs = (delta * delta).sum(axis=2)
    previous = np.zeros(costs.shape, dtype=int)
    for y in range(1, len(costs)):
        padded = np.pad(costs[y-1], 1, constant_values=np.inf)
        options = np.stack([padded[i:i+overlap] for i in range(3)])
        previous[y] = np.argmin(options, axis=0) - 1
        costs[y] += options.min(axis=0)
    seam = np.zeros(len(costs), dtype=int)
    seam[-1] = np.argmin(costs[-1])
    for y in range(len(seam)-1, 0, -1):
        seam[y-1] = seam[y] + previous[y, seam[y]]
    joined = np.arange(overlap) < seam[:, None]
    return np.concatenate([left[:, :-overlap], np.where(joined[:, :, None], a, b),
                           right[:, overlap:]], axis=1)


def grass_patch(b):
    # Copy irregular tufts from the original grass into a seamless turf repeat.
    # Stamp through the repeat boundaries as well, so no grid lines appear.
    rng = np.random.default_rng(23)
    turf = np.full((96, 128, 4), TURF, dtype=np.uint8)
    for _ in range(102):
        rx, ry = rng.integers([4, 2], [10, 6])
        sx, sy = rng.integers([28, 24], [99, 45])
        y, x = np.ogrid[-ry:ry+1, -rx:rx+1]
        dy, dx = np.where((x / rx)**2 + (y / ry)**2 <= 1)
        ox, oy = rng.integers([0, 0], [128, 96])
        tuft = b[sy+dy-ry, sx+dx-rx]
        detail = np.any(tuft != TURF, axis=1)
        turf[(oy+dy[detail]) % 96, (ox+dx[detail]) % 128] = tuft[detail]
    return turf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", type=Path)
    args = parser.parse_args()
    paths = [OUT / f"mini_mountain_source_{s}.png" for s in "ab"]
    if args.sources and len(args.sources) != 2:
        parser.error("Supply both original source sheets, A then B.")
    for src, dst in zip(args.sources, paths):
        shutil.copyfile(src, dst)
    a, b = (np.array(Image.open(path).convert("RGBA")) for path in paths)
    assert a.shape == b.shape == (256, 256, 4)
    # The 32x96 texture of each tile starts at the top of its 32x32 map cell.
    # The two extra rows draw the cliff face into the space below the plateau.
    grass = grass_patch(b)
    bare = b[36:132, 24:106]
    vines = b[36:132, 151:228]
    rugged = a[36:132, 34:113].copy()
    rugged[70:] = 0
    runs = compatible_faces(bare, vines, rugged)
    rims = grass_and_stone_rims(b)
    masks = [n for n in range(256) if complete_corners(n)]
    atlas = Image.new("RGBA", (16*T, ((len(masks)+15)//16)*96*len(runs)))
    for i, mask in enumerate(masks):
        for variation, face in enumerate(runs):
            tile = terrain_tile(mask, face, grass, rims[variation], variation)
            pos = ((i % 16)*T, (i//16 + 3*variation)*96)
            atlas.paste(Image.fromarray(tile), pos)
    atlas.save(OUT / "mini_mountain_atlas.png")

    build_stairs()
    (OUT / "mini_mountain_atlas.json").write_text(
        json.dumps({"masks": masks, "variants": len(runs)})+"\n", encoding="utf-8")


# Order matches the eight TileSet peering bits in the scene builder.
NEIGHBORS = [(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]


def complete_corners(mask):
    for bit in (1,3,5,7):
        if mask & (1 << bit):
            sides = (1 << (bit-1)) | (1 << ((bit+1)%8))
            if mask & sides != sides:
                return False
    return True


def compatible_faces(bare, vines, rugged):
    # All variants share a seam at the ends. Keep the rock, the overhanging
    # blades and the base from the same source column.
    costs = [np.abs(bare[:,x].astype(float)-bare[:,x+31]).mean()
             for x in range(bare.shape[1]-31)]
    start = int(np.argmin(costs))
    base = bare[:,start:start+32]
    compiled = []
    for patch in (base, vines[:,12:44], rugged[:,9:41], bare[:,36:68]):
        strip = join(base[:,:10],patch[:,2:30],8)
        strip = join(strip,base[:,-10:],8)
        # fill only actual holes between the lip and the attached bottom.
        result = strip.copy()
        for x in range(T):
            covered = np.flatnonzero(result[:,x,3])
            breaks = np.split(covered,np.flatnonzero(np.diff(covered)>3)+1)
            foot = max(breaks,key=len)[-1]
            result[foot+1:,x] = 0
            for y in range(foot+1):
                if not result[y,x,3]:
                    result[y,x] = result[y-1,x] if y else TURF
        compiled.append(result)
    return compiled


def grass_and_stone_rims(sheet):
    """Keep the original grass silhouette over a narrow band of matching cliff."""
    def strip(x, width):
        # A blade can reach the outer edge or reveal a few pixels of stone.
        # Keep the alpha gaps between blades, with real cliff pixels behind.
        foliage = sheet[7:39, x:x+width]
        y = np.arange(32)[:, None]
        u = np.arange(x, x+width)[None, :]
        stone = sheet[83 + y % 16, u].copy()
        # The low rim sits in the shadow of the grass overhang. Use a darker
        # value of the same stone so bright front-facing facets don't repeat
        # as a row of highlights around the entire shelf.
        stone[:, :, :3] = np.rint(stone[:, :, :3]*[0.78, 0.84, 0.80])
        return np.where(foliage[:, :, 3:] > 0, foliage, stone)

    bank = strip(19, 92)
    # Find a continuous repeat and keep its end columns on every variation.
    # This also matches two different variants chosen by the Godot brush.
    cost = [np.abs(bank[:, x].astype(int) - bank[:, x+31]).mean()
            for x in range(bank.shape[1]-31)]
    start = int(np.argmin(cost))
    base = bank[:, start:start+T]
    return [join(join(base[:, :11], strip(x, T)[:, 3:-3], 8), base[:, -11:], 8)
            for x in (30, 65, 154, 192)]


def rim_contour(mask, variation):
    """Measure the rounded perimeter across tile boundaries, in native pixels."""
    occupancy = np.zeros((3*T,3*T), dtype=np.uint8)
    for i,(dx,dy) in enumerate([(0,0)]+NEIGHBORS):
        if i == 0 or mask & (1 << (i-1)):
            x,y = (1+dx)*T,(1+dy)*T
            occupancy[y:y+T,x:x+T] = 255
    inset = Image.fromarray(occupancy).filter(ImageFilter.MinFilter(5))
    field = np.asarray(inset.filter(ImageFilter.GaussianBlur(8)), dtype=float)
    gy, gx = np.gradient(field)
    strength = np.maximum(np.hypot(gx, gy), 0.5)
    nx, ny = gx / strength, gy / strength
    distance = (field - 128) / strength

    # Small ledges meander around a long straight run. The end samples have
    # the same displacement for all variants so their outlines meet.
    yy, xx = np.indices(field.shape)
    def wobble(axis):
        t = (axis % T + 0.5) / T
        wave = np.sin(2*np.pi*t) + 0.45*np.sin(4*np.pi*t)
        accent = np.sin(np.pi*t)**2 * np.sin(2*np.pi*t + variation*1.4)
        return 0.65*wave + 1.45*accent

    distance -= 1.5 + (np.maximum(ny, 0)*wobble(xx) + abs(nx)*wobble(yy))
    # Use the structural outline for tall cliffs. A protruding grass tuft on
    # a lateral edge must not emit a vertical column of south-facing rock.
    structural = field >= 133
    return distance, nx, ny, structural


def terrain_tile(mask, face, grass, rim, variation):
    distance, nx, ny, structural = rim_contour(mask, variation)
    tile = np.zeros((96,T,4),dtype=np.uint8)
    region = np.s_[T:2*T, T:2*T]
    depth = distance[region]
    yy, xx = np.indices((T, T))
    offset = variation * T
    surface = grass[(yy+offset) % grass.shape[0], (xx+offset) % grass.shape[1]].copy()
    # Wrap one continuous strip around the bend using its local tangent.
    # The exposed rock gives way to real grass blades, then the plateau turf.
    along = np.rint((xx-15.5)*ny[region] - (yy-15.5)*nx[region] + 15.5).astype(int) % T
    light = 1.6*nx[region] + 1.4*np.sin((along+2)*2*np.pi/T)
    sample = np.rint(1 + depth*1.25 + light).astype(int)
    use_rim = (sample < len(rim)) & ((ny[region] > -0.75) | (np.abs(nx[region]) > 0.55))
    art = rim[np.clip(sample, 0, len(rim)-1), along]
    surface[use_rim] = art[use_rim]
    surface[surface[:, :, 3] == 0] = TURF
    inside = depth >= 0
    tile[:T][inside] = surface[inside]

    for x in range(T):
        col = structural[T:2*T,T+x]
        ends = np.flatnonzero(col & ~structural[T+1:2*T+1,T+x])
        for end in ends:
            # Keep the horizontal face level even on single-tile-wide shelves.
            # Where the contour turns north, the front follows the corner.
            for sy in np.flatnonzero(face[:,x,3]):
                ty = end + sy - 21
                if ty < 0 or ty >= 96:
                    continue
                if ty <= end and not col[ty]:
                    continue
                pixel = face[sy,x]
                # Where the side turns into the front wall, let its grass
                # silhouette meet the actual rock. An opaque rectangular
                # patch of turf at the head of the wall would cut the rim off.
                if (ty < end and tile[ty,x,3] and depth[ty,x] < 11
                        and abs(nx[T+ty,T+x]) > 0.5 and pixel[1] > pixel[0]):
                    continue
                tile[ty,x] = pixel
    return tile


if __name__ == "__main__":
    main()
