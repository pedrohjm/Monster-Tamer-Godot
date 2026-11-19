"""Estilo C do planalto: paredão de blocos de pedra em colunas, com a grama do jogo no topo.

    python tools/art/build_plateau_style_c.py

Saídas:
  art/tiles/plateau_c_face.png  paredão abaixo das bordas sul da grama: um tile alto
                                (32 x ROWS*32) por máscara, no layout de
                                DualGrid.ATLAS_BY_MASK com a linha multiplicada por ROWS,
                                VARIANTS cópias lado a lado (colunas + 4*v) de uma faixa de
                                64 px que emenda, para os blocos não repetirem a cada tile
  art/tiles/plateau_c_rim.png   atlas 4x4: fileira estreita de blocos nas laterais e no norte

Estilo (referências enviadas pelo usuário): blocos de pedra verde-oliva acinzentados,
empilhados em fileiras desencontradas; cada bloco tem a face de cima clara com um fio de
luz, o lado direito numa sombra azulada, cantos chanfrados e contorno marrom-escuro. As
pedras da primeira fileira sobem um pouco por cima da beirada da grama. O topo é a grama do
jogo (art/tiles/grass.png); a forma (alfa) dela define onde o paredão começa.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
GRASS = ROOT / "art/tiles/grass.png"
FACE_OUT = ROOT / "art/tiles/plateau_c_face.png"
RIM_OUT = ROOT / "art/tiles/plateau_c_rim.png"
T = 32
ROWS = 3
VARIANTS = 2
STRIP_W = T * VARIANTS
TOP_Y = 13          # linha do tile onde o paredão pode começar
OVERLAP = 3         # quanto a primeira fileira sobe por cima da beirada da grama
HEIGHT = 44         # altura do paredão (~1,4 tile)
SIDE_W = 7          # fileira de blocos nas laterais
NORTH_W = 4         # e no norte
SEED = 13

OUTLINE = (52, 48, 36)
SHADOW = (56, 65, 64)       # lado direito (azulado)
DARK = (74, 74, 56)
BODY = [(90, 91, 70), (96, 96, 76), (86, 86, 66)]
LIGHT = (104, 104, 84)
TOP = (114, 112, 88)        # face de cima
HILITE = (140, 140, 112)    # fio de luz na beirada de cima
GAP = (40, 46, 48)          # fresta funda entre blocos
GROUND = (86, 128, 52)      # base da grama de baixo (tile cheio de art/tiles/grass.png)
BLADE = [(59, 95, 49), (72, 110, 50), (87, 128, 54), (110, 150, 56), (127, 169, 57), (150, 190, 72)]
GROUND_SHADOW = (20, 36, 14)

ATLAS_BY_MASK = [
    (0, 3), (1, 3), (0, 0), (3, 0), (0, 2), (1, 0), (2, 3), (1, 1),
    (3, 3), (0, 1), (3, 2), (2, 0), (1, 2), (2, 2), (3, 1), (2, 1),
]


def draw_block(img: list[list[tuple | None]], x0: int, y0: int, w: int, h: int, body: tuple,
               chamfer: tuple[int, int, int, int], wrap: int | None, top_h: int) -> None:
    """Bloco de pedra: face de cima clara (top_h px) com fio de luz, corpo, um terço direito
    na sombra azulada, base escura, cantos chanfrados e contorno."""
    height = len(img)
    shade_w = max(2, w // 3)
    for j in range(h):
        y = y0 + j
        if not 0 <= y < height:
            continue
        for i in range(w):
            # chanfros: TL, TR, BL, BR
            if (j < chamfer[0] and i < chamfer[0] - j) or (j < chamfer[1] and w - 1 - i < chamfer[1] - j)                     or (h - 1 - j < chamfer[2] and i < chamfer[2] - (h - 1 - j))                     or (h - 1 - j < chamfer[3] and w - 1 - i < chamfer[3] - (h - 1 - j)):
                continue
            x = x0 + i
            if wrap is not None:
                x %= wrap
            elif not 0 <= x < len(img[0]):
                continue
            # contorno: borda do bloco, incluindo a diagonal dos chanfros
            edge = (i == 0 or i == w - 1 or j == 0 or j == h - 1
                    or (j < chamfer[0] and i == chamfer[0] - j) or (j < chamfer[1] and w - 1 - i == chamfer[1] - j)
                    or (h - 1 - j < chamfer[2] and i == chamfer[2] - (h - 1 - j))
                    or (h - 1 - j < chamfer[3] and w - 1 - i == chamfer[3] - (h - 1 - j)))
            if edge:
                c = OUTLINE
            elif j == 1 and i < w - shade_w:
                c = HILITE
            elif j <= top_h:
                c = TOP if i < w - shade_w else LIGHT
            elif i >= w - shade_w:
                c = SHADOW if i > w - shade_w or j > top_h + 1 else DARK
            elif j >= h - 3:
                c = DARK
            elif i == 1:
                c = LIGHT
            else:
                c = body
            img[y][x] = c


def build_strip(rng: random.Random) -> tuple[list[list[tuple | None]], list[int]]:
    """Faixa STRIP_W x (OVERLAP+HEIGHT) de blocos grandes em fileiras desencontradas, que
    emenda nas laterais. Cada fileira cobre a base da de cima. Devolve também a última linha
    de pedra de cada coluna."""
    h_total = OVERLAP + HEIGHT + 3
    img: list[list[tuple | None]] = [[None] * STRIP_W for _ in range(h_total)]
    rows = [(0, 17), (14, 17), (28, 17)]   # (topo, altura) das fileiras
    for y0, h in rows:
        x = rng.randint(0, 12)
        start = x
        while x < start + STRIP_W:
            w = rng.randint(10, 16)
            if start + STRIP_W - x < 9:
                w = start + STRIP_W - x + 1
            bh = h + rng.randint(-2, 1)
            by = y0 + rng.randint(-3, 2)
            ch = (rng.choice((2, 3, 4)), rng.choice((2, 3, 4)), rng.choice((1, 2)), rng.choice((1, 2, 3)))
            draw_block(img, x, by, w, bh, rng.choice(BODY), ch, STRIP_W, rng.choice((2, 3, 4)))
            x += w - 1   # blocos vizinhos dividem o contorno
    bottoms = [0] * STRIP_W
    for x in range(STRIP_W):
        last = max((y for y in range(h_total) if img[y][x] is not None), default=h_total - 1)
        bottoms[x] = last
    # Buracos entre blocos viram fresta funda (sombra azulada escura).
    for y in range(h_total):
        for x in range(STRIP_W):
            if img[y][x] is None and y < max(bottoms[x] - 1, 0):
                img[y][x] = GAP
    return img, bottoms


def edge_rows(alpha, tx: int, ty: int) -> list[int | None]:
    out: list[int | None] = []
    for x in range(T):
        ys = [y for y in range(T) if alpha[tx * T + x, ty * T + y] > 0]
        out.append(None if not ys or ys[-1] >= T - 2 else ys[-1])
    return out


def blades() -> tuple[list[int], list[int]]:
    rng = random.Random(29)
    hs, ss = [], []
    for x in range(T):
        v = 1.4 + 1.2 * math.sin(x * 0.7 + 0.5) + 0.8 * math.sin(x * 2.2 + 0.1) + rng.uniform(-0.8, 0.8)
        hs.append(max(0, min(3, round(v))))
        ss.append(rng.randint(2, 4))
    return hs, ss


def build_face(strip, bottoms, alpha) -> None:
    hs, ss = blades()
    face = Image.new("RGBA", (4 * T * VARIANTS, 4 * T * ROWS), (0, 0, 0, 0))
    fp = face.load()
    for mask in range(16):
        tl, tr, bl, br = bool(mask & 8), bool(mask & 4), bool(mask & 2), bool(mask & 1)
        if not ((tl and not bl) or (tr and not br)):
            continue
        ax, ay = ATLAS_BY_MASK[mask]
        rows = edge_rows(alpha, ax, ay)
        cols = [rows[x] is not None and ((x < T // 2 and tl and not bl) or (x >= T // 2 and tr and not br))
                for x in range(T)]
        ends = [x for x in range(T) if cols[x] and ((x > 0 and not cols[x - 1]) or (x < T - 1 and not cols[x + 1]))]
        for v in range(VARIANTS):
            ox, oy = (ax + 4 * v) * T, ay * ROWS * T
            for x in range(T):
                if not cols[x]:
                    continue
                sx = v * T + x
                d = min((abs(x - e) for e in ends), default=99)
                cut = {0: 4, 1: 2, 2: 1}.get(d, 0)
                top = max(TOP_Y, rows[x] - OVERLAP)
                # A faixa fica presa numa linha fixa (as fileiras alinhadas entre colunas).
                y_origin = TOP_Y + 4 - OVERLAP
                base = y_origin + bottoms[sx] - cut
                for y in range(top, base + 1):
                    sy = y - y_origin
                    if not 0 <= sy < len(strip):
                        continue
                    c = strip[sy][sx]
                    if c is None:
                        continue
                    if y == base or (d == 0):
                        c = OUTLINE if y == base or d == 0 else c
                    fp[ox + x, oy + y] = c + (255,)
                ground = base + 1
                if ground < ROWS * T:
                    fp[ox + x, oy + ground] = GROUND + (255,)
                for k in range(1, 1 + ss[x]):
                    if ground + k < ROWS * T:
                        fp[ox + x, oy + ground + k] = GROUND_SHADOW + (int(85 * (1 - (k - 1) / 4)),)
                for k in range(hs[x] + 1):
                    t = k / max(1, hs[x])
                    if 0 <= ground - k < ROWS * T:
                        fp[ox + x, oy + ground - k] = BLADE[min(len(BLADE) - 2, round(t * (len(BLADE) - 2)))] + (255,)
    face.save(FACE_OUT)


def build_rim(alpha, size: tuple[int, int]) -> None:
    """Fileira estreita de blocos nas laterais (empilhados na vertical; repete a cada 32 px)
    e beirada de blocos no norte."""
    cuts = [0, 7, 14, 22, 27]   # divisas dos blocos ao longo da lateral (período 32)
    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    rp = rim.load()
    for ty in range(4):
        for tx in range(4):
            def op(x: int, y: int) -> bool:
                return 0 <= x < T and 0 <= y < T and alpha[tx * T + x, ty * T + y] > 0

            for y in range(T):
                for x in range(T):
                    if op(x, y):
                        continue
                    dw = next((k for k in range(1, SIDE_W + 2) if op(x + k, y)), 0)
                    de = next((k for k in range(1, SIDE_W + 2) if op(x - k, y)), 0)
                    dn = next((k for k in range(1, NORTH_W + 2) if op(x, y + k)), 0)
                    if dw or de:
                        k = dw if dw and (not de or dw <= de) else de
                        west = k == dw
                        if k == SIDE_W + 1:
                            c = OUTLINE
                        else:
                            pos = y % T
                            first = max(c_ for c_ in cuts if c_ <= pos)
                            j = pos - first
                            if j == 0:
                                c = OUTLINE
                            elif j == 1:
                                c = HILITE
                            elif j == 2:
                                c = TOP
                            elif west:
                                c = LIGHT if k >= SIDE_W - 1 else BODY[0] if k > 2 else SHADOW
                            else:
                                c = SHADOW if k >= SIDE_W - 2 else DARK
                    elif dn:
                        c = OUTLINE if dn >= NORTH_W else HILITE if dn == NORTH_W - 1 else TOP if dn > 1 else DARK
                    else:
                        continue
                    rp[tx * T + x, ty * T + y] = c + (255,)
    rim.save(RIM_OUT)


def build() -> None:
    rng = random.Random(SEED)
    strip, bottoms = build_strip(rng)
    grass = Image.open(GRASS).convert("RGBA")
    alpha = grass.split()[3].load()
    if TOP_Y + 4 - OVERLAP + max(bottoms) + 6 > ROWS * T:
        raise SystemExit("paredão não cabe nas células do tile alto")
    build_face(strip, bottoms, alpha)
    build_rim(alpha, grass.size)
    print(f"salvo em {FACE_OUT.relative_to(ROOT)} e {RIM_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
