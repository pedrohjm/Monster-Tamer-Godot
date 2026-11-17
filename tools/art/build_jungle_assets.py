"""Gera os assets 32 px do bioma de selva a partir das cartelas feitas por IA.

Uso (na raiz do projeto):
    python -I tools/art/build_jungle_assets.py

Entradas: art/source/sheet_jungle_a.webp, sheet_jungle_b.webp e sheet_jungle_cliffs.webp.
Saídas:
    art/tiles/jungle_terrain.png   atlas 32x32 (terrenos e bloqueio)
    art/sprites/cliffs/*.png       segmentos de penhasco (2 tiles de largura, ~3 de altura)
    art/tiles/jungle_terrain.json  layout do atlas, lido por tools/build_region.gd
    art/sprites/props/*.png        props com origem nos pés

As cartelas não têm conjuntos de autotile completos, então as transições
(16 peças por camada, modo "Match Corners" do Godot) são geradas aqui a partir
das texturas de preenchimento. Cada camada é "terreno X por cima de qualquer
coisa", com transparência fora da máscara.
"""

import json
import math
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SHEET_A = ROOT / "art/source/sheet_jungle_a.webp"
SHEET_B = ROOT / "art/source/sheet_jungle_b.webp"
OUT_TILES = ROOT / "art/tiles"
OUT_PROPS = ROOT / "art/sprites/props"

T = 32  # tamanho do tile em px (Units.TILE no jogo)
COLS = 16
FRAMES = 4
OUTLINE_FILL = (38, 28, 30)

# ---------------------------------------------------------------- utilidades


def is_magenta(c):
    # Inclui a franja roxa escura (magenta misturado com o contorno).
    r, g, b = c[0], c[1], c[2]
    return r - g > 60 and b - g > 60 and abs(r - b) < 90


def load_sheets():
    b = Image.open(SHEET_B).convert("RGBA")
    px = b.load()
    for y in range(b.height):
        for x in range(b.width):
            if is_magenta(px[x, y]):
                px[x, y] = (0, 0, 0, 0)
    a = Image.open(SHEET_A).convert("RGBA")
    pa = a.load()
    for y in range(a.height):
        for x in range(a.width):
            c = pa[x, y]
            pa[x, y] = c[:3] + (255,) if c[3] >= 245 else (0, 0, 0, 0)
    return a, b


def crisp_resize(img, size):
    """Redimensiona sem franja colorida: pixels transparentes viram contorno
    escuro antes do filtro e o alfa final é binário."""
    img = img.copy()
    p = img.load()
    for y in range(img.height):
        for x in range(img.width):
            if p[x, y][3] == 0:
                p[x, y] = OUTLINE_FILL + (0,)
    rgb = img.convert("RGB").resize(size, Image.LANCZOS)
    alpha = img.split()[3].resize(size, Image.BILINEAR).point(lambda v: 255 if v >= 128 else 0)
    rgb.putalpha(alpha)
    return rgb


def trim(img, box, pad=1):
    piece = img.crop(box)
    bbox = piece.getbbox()
    if bbox is None:
        raise ValueError(f"recorte vazio: {box}")
    x0, y0, x1, y1 = bbox
    return piece.crop((max(0, x0 - pad), max(0, y0 - pad), min(piece.width, x1 + pad), min(piece.height, y1 + pad)))


def seamless(tile, axis_x=True, axis_y=True):
    """Torna um tile repetível misturando-o com a cópia deslocada meio tile."""
    w, h = tile.size
    src = tile.load()
    out = Image.new("RGBA", (w, h))
    dst = out.load()
    for y in range(h):
        for x in range(w):
            wx = min(x + 0.5, w - x - 0.5) / (w / 2) if axis_x else 1.0
            wy = min(y + 0.5, h - y - 0.5) / (h / 2) if axis_y else 1.0
            k = max(0.0, min(1.0, (min(wx, wy) - 0.15) / 0.55))
            k = k * k * (3 - 2 * k)
            a = src[x, y]
            sx = (x + w // 2) % w if axis_x else x
            sy = (y + h // 2) % h if axis_y else y
            b = src[sx, sy]
            dst[x, y] = tuple(int(a[i] * k + b[i] * (1 - k)) for i in range(3)) + (255,)
    return out


def fill_tile(sheet, box, inset=4):
    x0, y0, x1, y1 = box
    piece = sheet.crop((x0 + inset, y0 + inset, x1 - inset, y1 - inset))
    return seamless(piece.convert("RGB").resize((T, T), Image.LANCZOS).convert("RGBA"))


def square_crop(box):
    x0, y0, x1, y1 = box
    s = min(x1 - x0, y1 - y0) - 4
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    return (cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2)


def palette(img, n):
    q = img.convert("RGB").quantize(colors=n)
    pal = q.getpalette()[: n * 3]
    cols = [tuple(pal[i:i + 3]) for i in range(0, n * 3, 3)]
    return sorted(cols, key=lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


# ---------------------------------------------------------------- grama


def grass_tile(pal, seed, flowers=0):
    """Grama procedural repetível com a paleta tirada da cartela."""
    rng = random.Random(seed)
    img = Image.new("RGBA", (T, T))
    p = img.load()
    for y in range(T):
        for x in range(T):
            n = math.sin(2 * math.pi * (x / T + 2 * y / T) + seed) + math.sin(2 * math.pi * (3 * x / T - y / T) + seed * 2)
            p[x, y] = pal[2 if n < 0.4 else 3] + (255,)
    for _ in range(46):
        x, y = rng.randrange(T), rng.randrange(T)
        p[x, (y + 2) % T] = pal[1] + (255,)
        p[x, (y + 1) % T] = pal[3] + (255,)
        p[x, y] = pal[4 if rng.random() < 0.7 else 5] + (255,)
        if rng.random() < 0.4:
            p[(x + 1) % T, (y + 1) % T] = pal[4] + (255,)
    colors = [(236, 96, 120), (250, 236, 220), (250, 180, 70)]
    for _ in range(flowers):
        x, y = rng.randrange(T), rng.randrange(T)
        c = rng.choice(colors)
        p[x, y] = c + (255,)
        p[(x + 1) % T, y] = shade(c, 0.75) + (255,)
        p[x, (y + 1) % T] = pal[0] + (255,)
    return img


# ---------------------------------------------------------------- transições

TL, TR, BL, BR = 1, 2, 4, 8


def edge_noise(x, y, seed):
    """Ruído periódico em 32 px: peças vizinhas casam na borda."""
    v = 0.0
    tau = 2 * math.pi / T
    for k, (fx, fy, amp) in enumerate(((1, 1, 0.07), (2, 1, 0.045), (1, 3, 0.03), (3, 2, 0.02))):
        v += amp * math.sin(tau * fx * x + seed * (k + 1.7)) * math.cos(tau * fy * y + seed * (k + 0.9))
    return v


def mask_fn(bits, seed):
    c = [(bits >> i) & 1 for i in range(4)]

    def inside(x, y):
        u = min(1.0, max(0.0, (x + 0.5) / T))
        v = min(1.0, max(0.0, (y + 0.5) / T))
        top = c[0] * (1 - u) + c[1] * u
        bot = c[2] * (1 - u) + c[3] * u
        return top * (1 - v) + bot * v + edge_noise(x, y, seed) > 0.5

    return inside


def dist_out(inside, x, y, r):
    """Distância (1..r) até a máscara, procurando acima e dos lados; 0 se longe."""
    for d in range(1, r + 1):
        for dx, dy in ((0, -d), (-d, 0), (d, 0), (0, d)):
            if inside(x + dx, y + dy):
                return d
    return 0


def transition_tile(tex, bits, style, seed):
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    p = img.load()
    t = tex.load()
    inside = mask_fn(bits, seed)
    for y in range(T):
        for x in range(T):
            if inside(x, y):
                c = t[x, y]
                border = not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if border and style.get("outline"):
                    c = shade(c, style["outline"]) + (255,)
                elif style.get("lip") and not inside(x, y + 2):
                    c = shade(c, style["lip"]) + (255,)
                p[x, y] = c
            else:
                if style.get("shadow") and (inside(x, y - 1) or inside(x, y - 2) or inside(x - 1, y - 1)):
                    p[x, y] = (20, 30, 15, style["shadow"])
                elif style.get("foam"):
                    d = dist_out(inside, x, y, 2)
                    if d:
                        a = style["foam"][d - 1]
                        p[x, y] = (226, 250, 244, a)
                elif style.get("glow") and dist_out(inside, x, y, 1):
                    p[x, y] = style["glow"]
    return img


# ---------------------------------------------------------------- props

S_B = 32 / 56  # escala da cartela B (tiles de ~56 px)
S_A = 32 / 52  # escala da cartela A (tiles de ~52 px)

PROPS = {
    # nome: (cartela, caixa aproximada, escala)
    "palm_a": ("b", (474, 736, 578, 912), S_B),
    "palm_b": ("b", (712, 712, 858, 914), S_B),
    "banyan": ("b", (1000, 710, 1173, 916), S_B),
    "jungle_tree": ("b", (1379, 719, 1516, 913), S_B),
    "bridge_h": ("b", (1111, 470, 1437, 578), S_B),
    "bridge_v": ("b", (1487, 408, 1609, 660), S_B),
    "tent": ("a", (922, 426, 1021, 528), S_A * 1.4),
    "campfire": ("a", (793, 487, 845, 523), S_A),
    "barrel": ("a", (838, 428, 877, 472), S_A),
    "crate": ("a", (801, 429, 837, 468), S_A),
    "sign": ("a", (872, 374, 916, 414), S_A),
    "log": ("a", (240, 630, 324, 670), S_A),
    "bush": ("a", (325, 624, 381, 668), S_A),
    "fern_a": ("a", (358, 682, 403, 720), S_A),
    "fern_b": ("a", (416, 677, 448, 717), S_A),
    "fern_c": ("a", (460, 680, 495, 718), S_A),
    "flowers_pink": ("a", (80, 672, 131, 721), S_A),
    "flowers_orange": ("a", (138, 677, 180, 720), S_A),
    "flowers_red": ("a", (194, 673, 248, 725), S_A),
    "flowers_purple": ("a", (256, 673, 288, 717), S_A),
    "flowers_white": ("a", (302, 674, 343, 721), S_A),
    "mushrooms": ("a", (28, 683, 80, 719), S_A),
    "rock_small": ("a", (230, 591, 275, 622), S_A),
}

TALL_GRASS = {
    "tall_grass": [(52, 717, 116, 767), (140, 717, 204, 767), (226, 718, 291, 767), (314, 717, 378, 766)],
    "tall_grass_rustle": [(52, 778, 117, 827), (140, 778, 204, 827), (227, 778, 291, 827), (315, 776, 380, 826)],
    "tall_grass_top": [(52, 902, 113, 925), (139, 902, 200, 925), (227, 903, 288, 925), (315, 903, 376, 925)],
}


SHEET_CLIFFS = ROOT / "art/source/sheet_jungle_cliffs.webp"
OUT_CLIFFS = ROOT / "art/sprites/cliffs"
# Segmentos de penhasco (cartela própria). Escala única: frente reta = 64 px (2 tiles).
CLIFF_SCALE = 64 / 193
CLIFF_PIECES = {
    "front_0": (67, 25, 260, 318), "front_1": (309, 25, 503, 318),
    "front_2": (552, 25, 744, 318), "front_3": (792, 25, 985, 318),
    "corner_L": (1064, 24, 1227, 318), "corner_R": (1296, 24, 1464, 318),
    "end_L": (38, 366, 216, 638), "end_R": (249, 366, 421, 638),
    "inner_L": (460, 364, 620, 638), "inner_R": (652, 364, 808, 638),
    "diag_L": (852, 367, 1008, 638), "diag_R": (1050, 367, 1209, 638),
    "side_L": (1253, 365, 1333, 638), "side_R": (1408, 365, 1491, 638),
    "base_sand": (69, 684, 332, 980), "base_water": (388, 684, 658, 982),
    "stairs": (712, 684, 990, 980), "cave": (1045, 684, 1358, 984),
}


def build_cliffs():
    sheet = Image.open(SHEET_CLIFFS).convert("RGBA")
    p = sheet.load()
    for y in range(sheet.height):
        for x in range(sheet.width):
            if is_magenta(p[x, y]):
                p[x, y] = (0, 0, 0, 0)
    OUT_CLIFFS.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, box in CLIFF_PIECES.items():
        piece = trim(sheet, box, pad=0)
        size = (round(piece.width * CLIFF_SCALE), round(piece.height * CLIFF_SCALE))
        img = crisp_resize(piece, size)
        img.save(OUT_CLIFFS / f"{name}.png")
        meta[name] = list(img.size)
    for stale in ("edge_L", "edge_R"):
        for f in OUT_CLIFFS.glob(stale + ".png*"):
            f.unlink()
    # Paredes pequenas (não existem na cartela): frentes em 55% da escala, viram
    # props com colisão para quebrar a linha do penhasco e dar profundidade.
    for i in range(4):
        piece = trim(sheet, CLIFF_PIECES[f"front_{i}"], pad=0)
        size = (round(piece.width * CLIFF_SCALE * 0.55), round(piece.height * CLIFF_SCALE * 0.55))
        crisp_resize(piece, size).save(OUT_PROPS / f"rock_wall_{i}.png")
    return meta


def build_props(a, b):
    OUT_PROPS.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, (which, box, scale) in PROPS.items():
        piece = trim(a if which == "a" else b, box)
        size = (max(1, round(piece.width * scale)), max(1, round(piece.height * scale)))
        img = crisp_resize(piece, size)
        img.save(OUT_PROPS / f"{name}.png")
        meta[name] = list(img.size)
    for name, boxes in TALL_GRASS.items():
        for i, box in enumerate(boxes):
            piece = trim(b, box)
            # Um pouco maior que o tile para os tufos vizinhos se sobreporem sem buracos.
            size = (T + 4, T + 2) if name != "tall_grass_top" else (T + 4, round(piece.height * (T + 4) / piece.width))
            img = crisp_resize(piece, size)
            img.save(OUT_PROPS / f"{name}_{i}.png")
            meta[f"{name}_{i}"] = list(img.size)
    return meta


# ---------------------------------------------------------------- atlas


def main():
    a, b = load_sheets()

    deep = [fill_tile(b, square_crop(bx)) for bx in ((1205, 52, 1298, 120), (1317, 52, 1410, 120), (1429, 52, 1522, 120), (1542, 52, 1634, 120))]
    shallow = [fill_tile(b, square_crop(bx)) for bx in ((1205, 130, 1298, 200), (1317, 130, 1410, 200), (1429, 130, 1521, 200), (1542, 130, 1634, 200))]
    sand = [fill_tile(b, bx) for bx in ((360, 156, 416, 214), (418, 156, 474, 214), (360, 256, 416, 316))]
    dirt = [fill_tile(b, bx) for bx in ((360, 56, 416, 114), (418, 56, 474, 114), (476, 56, 533, 114))]
    # Paleta da grama ajustada à mão sobre a imagem de referência (verdes profundos).
    gpal = [(24, 58, 30), (38, 88, 36), (58, 124, 42), (74, 142, 46), (108, 172, 58), (150, 200, 76)]
    grass = [grass_tile(gpal, 3), grass_tile(gpal, 7), grass_tile(gpal, 11, flowers=2), grass_tile(gpal, 19, flowers=4)]

    layers = [
        # nome, texturas (1 por quadro), estilo da borda, variações do tile cheio
        ("shallow", shallow, {"glow": (190, 245, 235, 90)}, []),
        ("sand", [sand[0]], {"foam": (210, 110), "outline": 0.82}, sand[1:]),
        ("dirt", [dirt[0]], {"outline": 0.72}, dirt[1:]),
        ("grass", [grass[0]], {"outline": 0.55, "lip": 0.8, "shadow": 95}, grass[1:]),
    ]

    atlas = Image.new("RGBA", (COLS * T, 40 * T), (0, 0, 0, 0))
    layout = {"tile_size": T, "frames": FRAMES, "layers": {}}

    # Água funda animada: coluna 0, quadros empilhados nas linhas 0..3.
    for f, tex in enumerate(deep):
        atlas.paste(tex, (0, f * T))
    layout["deep_water"] = {"coords": [0, 0], "animated": True}
    # Bloqueio de colisão (vermelho translúcido, camada invisível no jogo).
    atlas.paste(Image.new("RGBA", (T, T), (220, 40, 40, 120)), (1 * T, 0))
    layout["blocker"] = [1, 0]

    row = FRAMES
    for li, (name, frames, style, variants) in enumerate(layers):
        animated = len(frames) > 1
        for f, tex in enumerate(frames):
            for bits in range(1, 16):
                tile = tex if bits == 15 else transition_tile(tex, bits, style, seed=li * 3 + 1)
                atlas.paste(tile, (bits * T, (row + f) * T))
        var_coords = []
        if variants:
            vrow = row + len(frames)
            for i, v in enumerate(variants):
                atlas.paste(v, (i * T, vrow * T))
                var_coords.append([i, vrow])
        layout["layers"][name] = {
            "row": row,
            "animated": animated,
            "variants": var_coords,
        }
        row += len(frames) + (1 if variants else 0)

    atlas = atlas.crop((0, 0, COLS * T, row * T))
    OUT_TILES.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT_TILES / "jungle_terrain.png")
    layout["props"] = build_props(a, b)
    layout["cliffs"] = build_cliffs()
    (OUT_TILES / "jungle_terrain.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")
    print("atlas", atlas.size, "props", len(layout["props"]))


if __name__ == "__main__":
    main()
