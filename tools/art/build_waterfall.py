"""Bake an animated spring, falling sheet and plunge pool on the 32 px grid."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

ROOT = Path(__file__).resolve().parents[2]
WIDTH, HEIGHT, FRAMES = 160, 144, 16
TILE = 32


def smooth(start, end, value):
    t = np.clip((value - start) / (end - start), 0, 1)
    return t * t * (3 - 2 * t)


def sample(rgb, x, y):
    coords = np.broadcast_arrays(y, x)
    return np.stack([map_coordinates(rgb[..., c], coords, order=1, mode="nearest")
                     for c in range(3)], axis=-1)


def silhouette(x, y):
    # Follow the wet rocks, the little spill at the left, and the source banks.
    outline = [(176,65),(214,43),(260,35),(349,18),(390,16),(467,35),(505,65),(505,97),
               (523,113),(523,131),(513,154),(518,182),(515,211),(528,233),
               (527,256),(547,280),(552,306),(563,328),(585,347),(592,357),
               (600,368),(586,392),(561,413),(500,434),(412,447),(322,442),
               (240,426),(198,409),(174,395),(161,382),(165,366),(183,352),
               (213,342),(230,324),(237,297),(241,280),(261,271),(269,253),
               (281,242),(287,211),(283,186),(286,168),(273,149),(251,139),
               (237,130),(213,126),(199,114),(181,103)]
    img = Image.new("L", (768,512))
    ImageDraw.Draw(img).polygon(outline, fill=1)
    inside = np.asarray(img, dtype=bool)
    edge = distance_transform_edt(inside) - distance_transform_edt(~inside)
    irregular = 1.5*np.sin(x*.32+y*.19) + 1.7*np.cos(y*.22-x*.26)
    # Keep the bank and cliff crisply cut, then dissolve the pool into the lake.
    fade = 9 + 32*smooth(380,432,y)
    return smooth(-2,fade,edge + irregular)


def make_frames():
    with Image.open(ROOT / "art/source/waterfall_reference.webp") as im:
        ref = np.asarray(im.convert("RGB").resize((768,512), Image.Resampling.LANCZOS),
                         dtype=np.float32)
    y, x = np.indices(ref.shape[:2], dtype=np.float32)
    red, green, blue = ref.transpose(2,0,1)
    water = gaussian_filter(smooth(-1,22,blue-red) * smooth(-12,18,green-red), .9)
    spill = smooth(153,183,y) * (1-smooth(330,383,y))
    # Two offset flows hand off at zero weight. Foam travels down through the
    # loop while dry boulders, lips and vegetation keep their registration.
    speed = (5 + 48*spill) * water
    pool = smooth(337,392,y)*water
    radial_x = np.clip((x-398)/135,-1.2,1.2)
    rim_y = 56 + .00195*(x-356)**2 + 3*np.sin(x*.064) + 2*np.cos(x*.117)
    rim_y -= 25*np.exp(-((x-371)/25)**2)
    depth = y - rim_y
    alpha = silhouette(x,y) * smooth(-6,-1,depth)
    rim = sample(ref, 98 + np.mod(x*.91,92), 112 + np.clip(depth,-6,8))
    # Grass blades hang slightly over the darker, damp lip of the spring.
    rim *= (0.74+0.26*(1-smooth(1,8,depth)))[...,None]
    bank = (1-smooth(1.7,8.2,depth + np.sin(.55*x)*2.8))[...,None]
    bank *= (1-smooth(90,115,y))[...,None]

    # Two stones break up the upstream bank at the spring. Their silhouettes
    # and reflected light come from the exposed boulder in the upper stream.
    rock = Image.new("L",(768,512))
    ImageDraw.Draw(rock).polygon([(200,63),(202,54),(209,50),(213,45),(223,44),
                                  (231,46),(238,51),(240,59),(245,63),(242,66),
                                  (232,68),(218,69),(209,67)],fill=255)
    rock_mask = gaussian_filter(np.asarray(rock,dtype=float)/255,.7)
    stones = []
    for cx,cy,scale in [(348,37,.98),(390,44,.57)]:
        sx, sy = (x-cx)/scale+222,(y-cy)/scale+57
        a = map_coordinates(rock_mask,[sy,sx],order=1,mode="constant")[...,None]
        stones.append((a, sample(ref,sx,sy)))

    for f in range(FRAMES):
        phase = f/FRAMES
        color = np.zeros_like(ref)
        for p, current in ((phase, .82), ((phase+.5)%1, 1.18)):
            weight = 1-abs(2*p-1)
            dx = p*(radial_x*19*pool + 1.8*np.sin(x*.046+y*.014)*spill*water)
            dy = p*(current*speed+9*pool)
            color += weight*sample(ref, x-dx, y-dy)
        # Keep the original contact shadows on either side of submerged rocks.
        color = ref + (.87*water[...,None])*(color-ref)
        color = color*(1-bank)+rim*bank
        opacity = alpha[...,None]
        for a, stone in stones:
            combined = a+(1-a)*opacity
            color = (a*stone+(1-a)*opacity*color)/np.maximum(combined,1e-6)
            opacity = combined
        frame = np.dstack((color,255*opacity)).clip(0,255).astype(np.uint8)
        # A constant world scale across the feeder, crest, sheet and foam.
        yield Image.fromarray(frame).resize(
            (WIDTH,HEIGHT),Image.Resampling.LANCZOS,box=(150,13,650,463))


def joined_tiles(single):
    """Cut synchronized left, repeatable middle and right sections at tile edges."""
    src = np.asarray(single.convert("RGBa"),dtype=float)
    center, half = WIDTH//2, TILE//2
    blend = smooth(6,26,np.arange(TILE))[None,:,None]
    strip = (1-blend)*src[:,center:center+TILE] + blend*src[:,center-TILE:center]
    yield single
    for left, right in ((True,False),(False,False),(False,True)):
        tile = np.zeros_like(src)
        if left:
            tile[:,:center] = src[:,:center]
        else:
            tile[:,center-half:center] = strip[:,half:]
        if right:
            tile[:,center:] = src[:,center:]
        else:
            tile[:,center:center+half] = strip[:,:half]
        yield Image.frombytes("RGBa",(WIDTH,HEIGHT),tile.round().astype("uint8").tobytes()).convert("RGBA")


def build():
    atlas = Image.new("RGBA",(WIDTH*FRAMES,HEIGHT*4))
    for index, frame in enumerate(make_frames()):
        for row, tile in enumerate(joined_tiles(frame)):
            atlas.paste(tile,(index*WIDTH,row*HEIGHT))
    atlas.save(ROOT / "art/tiles/waterfall.png",optimize=True)


if __name__ == "__main__":
    build()
