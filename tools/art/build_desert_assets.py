"""Gera os assets 32 px do bioma de deserto (transição grama -> deserto).

Uso (na raiz do projeto, depois de build_jungle_assets.py):
    python -I tools/art/build_desert_assets.py

Não existe cartela de deserto ainda. Por isso:
  * água e grama vêm das mesmas fontes da selva (água da cartela B, grama procedural);
  * areia dourada e trilha são texturas procedurais repetíveis;
  * penhascos (mesas) são os segmentos da selva recoloridos: rocha -> arenito
    avermelhado, vegetação do topo -> crosta de areia;
  * props do deserto (cactos, árvore seca, ruínas, arco de pedra, templo, braseiro,
    vaso, cerca, poste) são desenhados aqui em pixel art; alguns props da selva são
    recoloridos (arbusto seco, capim seco, árvore florida, pedras de arenito).
Quando houver uma cartela de deserto, trocar os geradores pelos recortes.

Saídas:
    art/tiles/desert_terrain.png / desert_terrain.json
    art/sprites/cliffs_desert/*.png
    art/sprites/props/*.png (só os novos nomes, listados em DESERT_PROPS)
"""

import colorsys
import importlib.util
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("jungle", HERE / "build_jungle_assets.py")
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)

ROOT = J.ROOT
T = J.T
OUT_TILES = ROOT / "art/tiles"
OUT_PROPS = ROOT / "art/sprites/props"
OUT_CLIFFS = ROOT / "art/sprites/cliffs_desert"

OUTLINE = (52, 30, 24)

# Rampas (escuro -> claro) tiradas das imagens de referência.
SAND_RAMP = [(176, 116, 58), (204, 146, 76), (226, 172, 96), (238, 192, 116), (248, 214, 146)]
ROCK_RAMP = [(54, 24, 22), (96, 40, 30), (140, 62, 40), (180, 92, 54), (212, 126, 74), (236, 166, 104)]
CRUST_RAMP = [(150, 92, 50), (196, 136, 72), (224, 168, 94), (240, 194, 120), (250, 220, 156)]
STONE_RAMP = [(70, 58, 52), (122, 106, 90), (168, 152, 124), (204, 190, 156), (230, 220, 188)]
WOOD_RAMP = [(52, 32, 24), (98, 60, 36), (140, 90, 50), (172, 118, 66)]
CACTUS_RAMP = [(28, 62, 36), (46, 104, 46), (72, 142, 56), (110, 178, 72), (156, 206, 100)]
PINK_RAMP = [(110, 40, 80), (176, 70, 120), (224, 110, 160), (244, 156, 196), (252, 206, 226)]
DRY_RAMP = [(92, 70, 30), (140, 112, 44), (184, 152, 62), (214, 186, 92), (236, 214, 130)]
OLIVE_RAMP = [(40, 52, 26), (70, 86, 36), (108, 120, 50), (146, 152, 70), (186, 186, 100)]


def lerp_ramp(ramp, t):
    t = max(0.0, min(1.0, t)) * (len(ramp) - 1)
    i = min(int(t), len(ramp) - 2)
    f = t - i
    a, b = ramp[i], ramp[i + 1]
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


def lum(c):
    return (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]) / 255.0


# ------------------------------------------------------------------ recolor


def recolor(img, rules, lo=0.08, hi=0.85):
    """Recolore por luminância. rules: lista de (teste(h, s, v), rampa); o primeiro
    teste que bater decide a rampa; sem regra, o pixel fica igual."""
    out = img.copy()
    p = out.load()
    for y in range(out.height):
        for x in range(out.width):
            c = p[x, y]
            if c[3] == 0:
                continue
            h, s, v = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
            for test, ramp in rules:
                if test(h * 360, s, v):
                    if ramp is None:
                        break
                    t = (lum(c) - lo) / (hi - lo)
                    p[x, y] = lerp_ramp(ramp, t) + (c[3],)
                    break
    return out


def is_green(h, s, v):
    return 60 <= h <= 175 and s > 0.2


def anything(h, s, v):
    return True


def is_water(h, s, v):
    # Água e espuma de base_water: ciano/azul, ou quase branca.
    return (165 <= h <= 260 and s > 0.15) or (s < 0.12 and v > 0.85)


def to_desert_rock(img):
    return recolor(img, [(is_water, None), (is_green, CRUST_RAMP), (anything, ROCK_RAMP)], lo=0.06, hi=0.62)


# ------------------------------------------------------------------ desenho


def shade_mask(mask, ramp, light=(-0.7, -0.7), ribs=0, rng=None, outline=OUTLINE, base=0.55):
    """Pinta uma máscara booleana (lista de linhas) com luz vinda de cima/esquerda,
    contorno escuro e, opcionalmente, nervuras verticais (cactos)."""
    h = len(mask)
    w = len(mask[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    p = img.load()

    def m(x, y):
        return 0 <= x < w and 0 <= y < h and mask[y][x]

    for y in range(h):
        # Extensão horizontal de cada trecho da linha, para luz "cilíndrica".
        x = 0
        while x < w:
            if not mask[y][x]:
                x += 1
                continue
            x0 = x
            while x + 1 < w and mask[y][x + 1]:
                x += 1
            x1 = x
            for xi in range(x0, x1 + 1):
                u = 0.5 if x1 == x0 else (xi - x0) / (x1 - x0)
                t = base + light[0] * (u - 0.5) * 0.9
                if not m(xi, y - 1):
                    t += 0.25
                if not m(xi, y + 1):
                    t -= 0.2
                if ribs and x1 - x0 >= 4 and (xi - x0) % ribs == ribs - 1 and xi != x1:
                    t -= 0.22
                if rng is not None:
                    t += rng.uniform(-0.06, 0.06)
                p[xi, y] = lerp_ramp(ramp, t) + (255,)
            x += 1
    for y in range(h):
        for x in range(w):
            if mask[y][x] and not all(m(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                p[x, y] = outline + (255,)
    return img


def empty_mask(w, h):
    return [[False] * w for _ in range(h)]


def rect(mask, x0, y0, x1, y1):
    for y in range(max(0, y0), min(len(mask), y1 + 1)):
        for x in range(max(0, x0), min(len(mask[0]), x1 + 1)):
            mask[y][x] = True


def ellipse(mask, cx, cy, rx, ry, value=True):
    for y in range(len(mask)):
        for x in range(len(mask[0])):
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                mask[y][x] = value


def capsule(mask, x0, y0, x1, y1):
    """Retângulo vertical com pontas arredondadas."""
    r = (x1 - x0 + 1) / 2
    cx = (x0 + x1 + 1) / 2
    rect(mask, x0, y0 + int(r), x1, y1)
    ellipse(mask, cx, y0 + r, r, r)


def foot_shadow(img, rx, ry=3, alpha=70):
    """Sombra elíptica nos pés, por baixo do sprite."""
    w, h = img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    cx = w / 2
    d.ellipse((cx - rx, h - 1 - ry * 2, cx + rx, h - 1), fill=(60, 30, 20, alpha))
    out.alpha_composite(img)
    return out


def pad_canvas(img, w, h, bottom=0):
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img, ((w - img.width) // 2, h - img.height - bottom), img)
    return out


# ------------------------------------------------------------------ props desenhados


def cactus_tall(seed, arms=2):
    rng = random.Random(seed)
    w, h = 26, 44
    mask = empty_mask(w, h)
    capsule(mask, 9, 2, 16, h - 2)
    # Braço esquerdo: sai do tronco, dobra para cima.
    ly = rng.randint(17, 22)
    rect(mask, 3, ly, 9, ly + 4)
    capsule(mask, 2, ly - 11, 6, ly + 4)
    if arms > 1:
        ry = rng.randint(12, 16)
        rect(mask, 16, ry, 22, ry + 4)
        capsule(mask, 19, ry - 8, 23, ry + 4)
    img = shade_mask(mask, CACTUS_RAMP, ribs=3, rng=rng)
    p = img.load()
    # Espinhos claros e uma flor no topo.
    for _ in range(22):
        x, y = rng.randrange(w), rng.randrange(h)
        if mask[y][x] and p[x, y][:3] != OUTLINE:
            p[x, y] = (236, 230, 190, 255)
    for dx, dy, c in ((12, 1, PINK_RAMP[2]), (13, 1, PINK_RAMP[3]), (12, 0, PINK_RAMP[3]), (13, 0, PINK_RAMP[2])):
        p[dx, dy] = c + (255,)
    return foot_shadow(pad_canvas(img, w + 4, h + 3, bottom=2), 8)


def cactus_barrel(seed):
    rng = random.Random(seed)
    w, h = 18, 16
    mask = empty_mask(w, h)
    ellipse(mask, 9, 9, 8, 7)
    img = shade_mask(mask, CACTUS_RAMP, ribs=3, rng=rng)
    p = img.load()
    for x, y in ((8, 2), (9, 2), (8, 1), (9, 1), (10, 2), (7, 2)):
        p[x, y] = PINK_RAMP[2 + (x + y) % 2] + (255,)
    for _ in range(10):
        x, y = rng.randrange(w), rng.randrange(h)
        if mask[y][x] and p[x, y][:3] != OUTLINE and y > 3:
            p[x, y] = (236, 230, 190, 255)
    return foot_shadow(pad_canvas(img, w + 4, h + 3, bottom=2), 8)


def cactus_pear(seed):
    """Palma (pads ovais empilhados)."""
    rng = random.Random(seed)
    w, h = 26, 26
    pads = [(13, 18, 6, 7), (7, 10, 5, 6), (19, 9, 5, 6), (13, 4, 4, 4)]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for cx, cy, rx, ry in pads:
        mask = empty_mask(w, h)
        ellipse(mask, cx, cy, rx, ry)
        img.alpha_composite(shade_mask(mask, CACTUS_RAMP, rng=rng))
    p = img.load()
    for cx, cy, rx, ry in pads[1:]:
        p[int(cx), int(cy - ry)] = PINK_RAMP[3] + (255,)
    for _ in range(14):
        x, y = rng.randrange(w), rng.randrange(h)
        if p[x, y][3] and p[x, y][:3] != OUTLINE:
            p[x, y] = (236, 230, 190, 255)
    return foot_shadow(pad_canvas(img, w + 2, h + 3, bottom=2), 9)


def dead_tree(seed):
    rng = random.Random(seed)
    w, h = 44, 52
    mask = empty_mask(w, h)

    def branch(x, y, ang, length, thick, depth):
        for i in range(int(length)):
            px = x + math.cos(ang) * i
            py = y - math.sin(ang) * i
            r = max(0.6, thick * (1 - i / length * 0.5))
            ellipse(mask, px, py, r, r)
        ex, ey = x + math.cos(ang) * length, y - math.sin(ang) * length
        if depth > 0:
            for da in (-0.55, 0.5):
                branch(ex, ey, ang + da + rng.uniform(-0.2, 0.2), length * rng.uniform(0.55, 0.75), thick * 0.62, depth - 1)

    rect(mask, 19, h - 6, 25, h - 3)
    branch(22, h - 4, math.pi / 2 + rng.uniform(-0.1, 0.1), 20, 3.2, 3)
    img = shade_mask(mask, WOOD_RAMP + [(196, 150, 96)], rng=rng)
    return foot_shadow(img, 9)


def ruin_pillar(seed, height):
    rng = random.Random(seed)
    w = 20
    h = height
    mask = empty_mask(w, h)
    rect(mask, 1, h - 6, w - 2, h - 1)          # base
    rect(mask, 4, 6, w - 5, h - 6)              # fuste
    rect(mask, 2, 2, w - 3, 7)                  # capitel
    # Topo quebrado: corta um dente irregular.
    for x in range(w):
        cut = int(2 + 3 * abs(math.sin(x * 0.9 + seed)))
        for y in range(0, min(h, cut)):
            mask[y][x] = False
    img = shade_mask(mask, STONE_RAMP, rng=rng)
    p = img.load()
    # Juntas dos blocos e caneluras.
    for y in range(10, h - 6, 9):
        for x in range(5, w - 5):
            if p[x, y][3] and p[x, y][:3] != OUTLINE:
                p[x, y] = STONE_RAMP[1] + (255,)
    for x in (7, 12):
        for y in range(8, h - 6):
            if p[x, y][3] and p[x, y][:3] != OUTLINE and y % 9 != 1:
                p[x, y] = lerp_ramp(STONE_RAMP, 0.4) + (255,)
    return foot_shadow(img, 9)


def ruin_gate(seed):
    """Portal de ruína: dois pilares e uma verga de blocos."""
    rng = random.Random(seed)
    w, h = 64, 56
    mask = empty_mask(w, h)
    for x0 in (3, w - 17):
        rect(mask, x0, 10, x0 + 13, h - 6)
        rect(mask, x0 - 2, h - 6, x0 + 15, h - 1)
    rect(mask, 0, 3, w - 1, 12)
    for x in range(w):  # topo gasto
        if math.sin(x * 0.7 + seed) > 0.6:
            mask[3][x] = False
    img = shade_mask(mask, STONE_RAMP, rng=rng)
    p = img.load()
    for x in range(8, w, 12):
        for y in range(4, 12):
            if p[x, y][3] and p[x, y][:3] != OUTLINE:
                p[x, y] = STONE_RAMP[1] + (255,)
    for x0 in (3, w - 17):
        for y in range(18, h - 6, 9):
            for x in range(x0 + 1, x0 + 13):
                if p[x, y][3] and p[x, y][:3] != OUTLINE:
                    p[x, y] = STONE_RAMP[1] + (255,)
    # Musgo seco/areia nos topos.
    for x in range(w):
        for y in range(3, 7):
            if p[x, y][3] and p[x, y][:3] != OUTLINE and rng.random() < 0.35:
                p[x, y] = CRUST_RAMP[3] + (255,)
    return foot_shadow(img, 30)


def clay_pot(seed):
    rng = random.Random(seed)
    w, h = 14, 17
    mask = empty_mask(w, h)
    ellipse(mask, 7, 10.5, 6.5, 6)
    rect(mask, 4, 1, 9, 5)
    rect(mask, 3, 0, 10, 1)
    ramp = [(80, 36, 22), (140, 66, 38), (186, 98, 56), (220, 140, 86), (240, 178, 124)]
    img = shade_mask(mask, ramp, rng=rng)
    p = img.load()
    for x in range(2, 12):
        if p[x, 9][3] and p[x, 9][:3] != OUTLINE:
            p[x, 9] = (236, 214, 170, 255)
    return foot_shadow(pad_canvas(img, w + 4, h + 2, bottom=1), 6)


def brazier(seed):
    rng = random.Random(seed)
    w, h = 18, 30
    mask = empty_mask(w, h)
    rect(mask, 6, 14, 11, h - 3)
    rect(mask, 4, h - 4, 13, h - 1)
    ellipse(mask, 9, 13, 8, 4)
    img = shade_mask(mask, STONE_RAMP, rng=rng)
    flame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fp = flame.load()
    fire = [(170, 40, 20), (236, 96, 30), (252, 170, 50), (255, 236, 150)]
    for y in range(0, 12):
        for x in range(w):
            r = (12 - y) / 12 * 6.5 + 0.5
            dx = abs(x - 9 + 0.5 * math.sin(y * 0.9))
            if dx < r * (0.6 + 0.4 * math.sin(y * 0.5 + 1)) and y > 1:
                t = 1 - dx / r * 0.7 - (12 - y) / 24
                fp[x, y] = fire[max(0, min(3, int(t * 4)))] + (255,)
    img.alpha_composite(flame)
    return foot_shadow(img, 6)


def fence(seed):
    w, h = 36, 22
    mask = empty_mask(w, h)
    for x0 in (2, 30):
        rect(mask, x0, 1, x0 + 3, h - 1)
    rect(mask, 0, 5, w - 1, 8)
    rect(mask, 0, 12, w - 1, 15)
    img = shade_mask(mask, WOOD_RAMP + [(196, 140, 84)], rng=random.Random(seed))
    return img


def lamp_post(seed):
    w, h = 22, 50
    mask = empty_mask(w, h)
    rect(mask, 4, 4, 8, h - 1)
    rect(mask, 2, h - 4, 10, h - 1)
    rect(mask, 4, 4, 17, 7)
    img = shade_mask(mask, WOOD_RAMP + [(196, 140, 84)], rng=random.Random(seed))
    lamp = empty_mask(w, h)
    rect(lamp, 13, 10, 20, 20)
    lim = shade_mask(lamp, STONE_RAMP)
    lp = lim.load()
    for y in range(12, 19):
        for x in range(15, 19):
            lp[x, y] = ((255, 236, 150) if (x + y) % 3 else (252, 190, 70)) + (255,)
    img.alpha_composite(lim)
    d = ImageDraw.Draw(img)
    d.line((16, 8, 16, 10), fill=OUTLINE + (255,))
    return img


def sand_arch(rock):
    """Arco natural de arenito montado com os segmentos de penhasco recoloridos."""
    side_l, side_r, front = rock["side_L"], rock["side_R"], rock["front_0"]
    w, h = 132, 104
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    top = front.crop((0, 0, front.width, 46))
    for x in range(0, w, front.width - 8):
        img.alpha_composite(top, (min(x, w - front.width), 0))
    img.alpha_composite(side_l, (2, h - side_l.height))
    img.alpha_composite(side_r, (w - side_r.width - 2, h - side_r.height))
    # Vão do arco: elipse transparente com borda sombreada.
    p = img.load()
    cx, cy, rx, ry = w / 2, h + 4, w / 2 - 26, h - 30
    inside = lambda x, y: ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1
    for y in range(h):
        for x in range(w):
            if inside(x, y):
                p[x, y] = (0, 0, 0, 0)
            elif p[x, y][3] and (inside(x, y + 1) or inside(x, y + 2)):
                p[x, y] = OUTLINE + (255,)
            elif p[x, y][3] and (inside(x, y + 3) or inside(x + 2, y + 2) or inside(x - 2, y + 2)):
                p[x, y] = ROCK_RAMP[1] + (255,)
    return foot_shadow(img, 60, ry=4, alpha=60)


def temple_piece(rock):
    """Fachada de templo encaixada na frente do penhasco (substitui a caverna)."""
    f0, f1 = rock["front_1"], rock["front_2"]
    w, h = 112, f0.height
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.alpha_composite(f0, (0, 0))
    img.alpha_composite(f1, (w - f1.width, 0))
    mid = rock["front_3"]
    img.alpha_composite(mid, ((w - mid.width) // 2, 0))
    fw, fh = 80, 70
    fx, fy = (w - fw) // 2, h - fh - 2
    mask = empty_mask(fw, fh)
    rect(mask, 4, 14, fw - 5, fh - 1)             # corpo
    rect(mask, 0, 8, fw - 1, 15)                  # cornija
    for i in range(3):                            # frontão em degraus
        rect(mask, 12 + i * 8, 8 - (i + 1) * 3, fw - 13 - i * 8, 8)
    facade = shade_mask(mask, STONE_RAMP, rng=random.Random(4), base=0.62)
    p = facade.load()
    ok = lambda x, y: p[x, y][3] and p[x, y][:3] != OUTLINE
    for y in range(20, fh - 1, 8):  # juntas
        for x in range(5, fw - 5):
            if ok(x, y):
                p[x, y] = STONE_RAMP[2] + (255,)
    for cx in (12, 22, fw - 23, fw - 13):  # colunas
        for y in range(16, fh - 4):
            for x in (cx - 3, cx + 3):
                p[x, y] = STONE_RAMP[1] + (255,)
            p[cx - 2, y] = STONE_RAMP[4] + (255,)
    # Porta escura com degradê e degraus.
    dw, dh = 26, 36
    dx0, dy0 = (fw - dw) // 2, fh - dh - 4
    for y in range(dy0, dy0 + dh):
        for x in range(dx0, dx0 + dw):
            t = (y - dy0) / dh
            p[x, y] = (int(14 + 20 * t), int(10 + 14 * t), int(12 + 10 * t), 255)
    for x in range(dx0 - 1, dx0 + dw + 1):
        p[x, dy0 - 1] = OUTLINE + (255,)
    for i in range(3):
        for x in range(dx0 - 4 - i * 3, dx0 + dw + 4 + i * 3):
            if 0 <= x < fw:
                p[x, fh - 4 + i] = (STONE_RAMP[3] if i % 2 == 0 else STONE_RAMP[2]) + (255,)
    # Símbolo no frontão (losango).
    for d in range(-3, 4):
        p[fw // 2 + d, 4 + abs(d) // 2] = (230, 170, 70, 255)
    img.alpha_composite(facade, (fx, fy))
    # Tochas nas laterais.
    for tx in (fx + 2, fx + fw - 8):
        for y in range(fy + 24, fy + 34):
            img.putpixel((tx + 2, y), WOOD_RAMP[1] + (255,))
            img.putpixel((tx + 3, y), WOOD_RAMP[2] + (255,))
        for (ox, oy, c) in ((2, -1, (236, 96, 30)), (3, -1, (252, 170, 50)), (2, -2, (252, 170, 50)),
                            (3, -2, (255, 236, 150)), (2, -3, (236, 96, 30)), (1, 0, (236, 96, 30)), (4, 0, (236, 96, 30))):
            img.putpixel((tx + ox, fy + 24 + oy), c + (255,))
    return img


# ------------------------------------------------------------------ terreno procedural


def sand_tile(seed, ripples=True, pebbles=0, cracks=False):
    rng = random.Random(seed)
    img = Image.new("RGBA", (T, T))
    p = img.load()
    tau = 2 * math.pi / T
    for y in range(T):
        for x in range(T):
            n = 0.55 + 0.07 * math.sin(tau * (x + 2 * y) + seed) + 0.05 * math.sin(tau * (3 * x - y) + seed * 2)
            if ripples:
                r = math.sin(tau * (2 * y + x) * 1 + 1.3 * math.sin(tau * x * 1 + seed))
                if r > 0.86:
                    n += 0.2
                elif r < -0.9:
                    n -= 0.16
            p[x, y] = lerp_ramp(SAND_RAMP, n) + (255,)
    for _ in range(40):
        x, y = rng.randrange(T), rng.randrange(T)
        p[x, y] = lerp_ramp(SAND_RAMP, rng.choice((0.25, 0.85, 0.95))) + (255,)
    for _ in range(pebbles):
        x, y = rng.randrange(T), rng.randrange(T)
        p[x, y] = STONE_RAMP[3] + (255,)
        p[(x + 1) % T, y] = STONE_RAMP[2] + (255,)
        p[x, (y + 1) % T] = SAND_RAMP[0] + (255,)
    if cracks:
        x, y = rng.randrange(T), rng.randrange(T)
        for _ in range(26):
            p[x % T, y % T] = SAND_RAMP[0] + (255,)
            x += rng.choice((1, 1, 0, -1))
            y += rng.choice((1, 0, 0, -1))
    return img


def path_tile(seed, stones=0):
    rng = random.Random(seed)
    ramp = [(130, 82, 46), (164, 108, 60), (190, 134, 78), (210, 158, 98), (226, 182, 124)]
    img = Image.new("RGBA", (T, T))
    p = img.load()
    tau = 2 * math.pi / T
    for y in range(T):
        for x in range(T):
            n = 0.5 + 0.09 * math.sin(tau * (x + y) + seed) + 0.07 * math.cos(tau * (2 * x - y) + seed)
            p[x, y] = lerp_ramp(ramp, n) + (255,)
    for _ in range(50):
        x, y = rng.randrange(T), rng.randrange(T)
        p[x, y] = lerp_ramp(ramp, rng.choice((0.15, 0.8))) + (255,)
    for _ in range(stones):
        cx, cy = rng.randrange(T), rng.randrange(T)
        rx, ry = rng.randint(3, 5), rng.randint(2, 3)
        for y in range(-ry, ry + 1):
            for x in range(-rx, rx + 1):
                d = (x / rx) ** 2 + (y / ry) ** 2
                if d <= 1:
                    c = STONE_RAMP[3] if y < 0 else STONE_RAMP[2]
                    if d > 0.6:
                        c = STONE_RAMP[1]
                    p[(cx + x) % T, (cy + y) % T] = c + (255,)
    return img


# ------------------------------------------------------------------ main


# Recortes da selva reaproveitados com outra cor (cartela, caixa, escala, rampa, regra).
RECOLORED = {
    "dry_bush": ("bush", OLIVE_RAMP),
    "dry_grass_0": ("fern_a", DRY_RAMP),
    "dry_grass_1": ("fern_b", DRY_RAMP),
    "dry_grass_2": ("fern_c", DRY_RAMP),
}


def build_props(a, b, rock):
    meta = {}

    def save(name, img):
        img.save(OUT_PROPS / f"{name}.png")
        meta[name] = list(img.size)

    for name, (src, ramp) in RECOLORED.items():
        which, box, scale = J.PROPS[src]
        piece = J.trim(a if which == "a" else b, box)
        img = J.crisp_resize(piece, (round(piece.width * scale), round(piece.height * scale)))
        save(name, recolor(img, [(is_green, ramp)], lo=0.1, hi=0.75))
    # Árvore florida: folhagem rosa.
    which, box, scale = J.PROPS["jungle_tree"]
    piece = J.trim(b, box)
    tree = J.crisp_resize(piece, (round(piece.width * scale), round(piece.height * scale)))
    save("blossom_tree", recolor(tree, [(is_green, PINK_RAMP)], lo=0.1, hi=0.8))
    # Pedras de arenito (pequena e grande).
    which, box, scale = J.PROPS["rock_small"]
    piece = J.trim(a, box)
    for name, k in (("sand_rock", 1.0), ("sand_boulder", 1.8)):
        img = J.crisp_resize(piece, (round(piece.width * scale * k), round(piece.height * scale * k)))
        save(name, recolor(img, [(anything, ROCK_RAMP[1:])], lo=0.15, hi=0.8))
    for i in range(4):
        wall = Image.open(OUT_PROPS / f"rock_wall_{i}.png").convert("RGBA")
        save(f"sandstone_wall_{i}", to_desert_rock(wall))

    save("cactus_tall", cactus_tall(1, arms=2))
    save("cactus_short", cactus_tall(5, arms=1))
    save("cactus_barrel", cactus_barrel(2))
    save("cactus_pear", cactus_pear(3))
    save("dead_tree", dead_tree(8))
    save("ruin_pillar_tall", ruin_pillar(1, 46))
    save("ruin_pillar_short", ruin_pillar(2, 26))
    save("ruin_gate", ruin_gate(3))
    save("clay_pot", clay_pot(1))
    save("brazier", brazier(1))
    save("fence", fence(1))
    save("lamp_post", lamp_post(1))
    save("sand_arch", sand_arch(rock))
    return meta


def build_cliffs():
    sheet = Image.open(J.SHEET_CLIFFS).convert("RGBA")
    p = sheet.load()
    for y in range(sheet.height):
        for x in range(sheet.width):
            if J.is_magenta(p[x, y]):
                p[x, y] = (0, 0, 0, 0)
    OUT_CLIFFS.mkdir(parents=True, exist_ok=True)
    rock = {}
    meta = {}
    for name, box in J.CLIFF_PIECES.items():
        piece = J.trim(sheet, box, pad=0)
        size = (round(piece.width * J.CLIFF_SCALE), round(piece.height * J.CLIFF_SCALE))
        img = to_desert_rock(J.crisp_resize(piece, size))
        img.save(OUT_CLIFFS / f"{name}.png")
        rock[name] = img
        meta[name] = list(img.size)
    temple = temple_piece(rock)
    temple.save(OUT_CLIFFS / "temple.png")
    meta["temple"] = list(temple.size)
    return rock, meta


def main():
    a, b = J.load_sheets()

    deep = [J.fill_tile(b, J.square_crop(bx)) for bx in ((1205, 52, 1298, 120), (1317, 52, 1410, 120), (1429, 52, 1522, 120), (1542, 52, 1634, 120))]
    shallow = [J.fill_tile(b, J.square_crop(bx)) for bx in ((1205, 130, 1298, 200), (1317, 130, 1410, 200), (1429, 130, 1521, 200), (1542, 130, 1634, 200))]
    sand = [sand_tile(1), sand_tile(2, ripples=False, pebbles=3), sand_tile(3, pebbles=1), sand_tile(4, ripples=False, cracks=True)]
    path = [path_tile(1, stones=1), path_tile(2, stones=2), path_tile(3), path_tile(4, stones=1)]
    gpal = [(30, 70, 28), (50, 108, 36), (82, 148, 42), (102, 168, 48), (138, 194, 62), (180, 218, 88)]
    grass = [J.grass_tile(gpal, 3), J.grass_tile(gpal, 7), J.grass_tile(gpal, 11, flowers=2), J.grass_tile(gpal, 19, flowers=4)]

    layers = [
        ("shallow", shallow, {"glow": (190, 245, 235, 90)}, []),
        ("sand", [sand[0]], {"foam": (210, 110), "outline": 0.85}, sand[1:]),
        ("dirt", [path[0]], {"outline": 0.8}, path[1:]),
        ("grass", [grass[0]], {"outline": 0.55, "lip": 0.8, "shadow": 95}, grass[1:]),
    ]

    atlas = Image.new("RGBA", (J.COLS * T, 40 * T), (0, 0, 0, 0))
    layout = {"tile_size": T, "frames": J.FRAMES, "layers": {}}
    for f, tex in enumerate(deep):
        atlas.paste(tex, (0, f * T))
    layout["deep_water"] = {"coords": [0, 0], "animated": True}
    atlas.paste(Image.new("RGBA", (T, T), (220, 40, 40, 120)), (1 * T, 0))
    layout["blocker"] = [1, 0]

    row = J.FRAMES
    for li, (name, frames, style, variants) in enumerate(layers):
        for f, tex in enumerate(frames):
            for bits in range(1, 16):
                tile = tex if bits == 15 else J.transition_tile(tex, bits, style, seed=li * 3 + 1)
                atlas.paste(tile, (bits * T, (row + f) * T))
        var_coords = []
        if variants:
            vrow = row + len(frames)
            for i, v in enumerate(variants):
                atlas.paste(v, (i * T, vrow * T))
                var_coords.append([i, vrow])
        layout["layers"][name] = {"row": row, "animated": len(frames) > 1, "variants": var_coords}
        row += len(frames) + (1 if variants else 0)

    atlas = atlas.crop((0, 0, J.COLS * T, row * T))
    OUT_TILES.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT_TILES / "desert_terrain.png")
    rock, layout["cliffs"] = build_cliffs()
    layout["props"] = build_props(a, b, rock)
    (OUT_TILES / "desert_terrain.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")
    print("atlas", atlas.size, "props", len(layout["props"]), "cliffs", len(layout["cliffs"]))


if __name__ == "__main__":
    main()
