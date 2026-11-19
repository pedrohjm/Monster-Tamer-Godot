"""Estilo A do planalto: paredão tirado da cartela de IA art/source/cliff_sheet_a.webp.

    python tools/art/build_plateau_style_a.py

Saídas:
  art/tiles/plateau_a_face.png  paredão abaixo das bordas sul da grama: um tile alto
                                (32 x ROWS*32) por máscara no layout de
                                DualGrid.ATLAS_BY_MASK com a linha multiplicada por ROWS,
                                VARIANTS cópias lado a lado (colunas + 4*v) cortadas do
                                bloco de 4 tiles, para a pedra não repetir a cada tile

A cartela é arte de IA sem grade de pixels exata e com as linhas da grade desenhadas por
cima (~90 px por célula). Pegamos o bloco de paredão de 4x2 células (BLOCK), tiramos as
linhas da grade (GRID_COLS/GRID_ROWS, interpolando os dois lados), reduzimos para 32 px por célula e limitamos a paleta (PALETTE cores) para
virar pixel art no tamanho do jogo. O topo e a faixa de pedra das laterais/norte são os do
estilo B (art/tiles/cliff_grass_b.png e plateau_b_rim.png, de build_plateau_style_b.py, que
precisa rodar antes): a grama (pixels verdes) de cada peça define onde o paredão começa, e
ele cobre a pedra baixa que o tileset B já tem nas peças de borda sul.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / "art/source/cliff_sheet_a.webp"
GRASS = ROOT / "art/tiles/cliff_grass_b.png"   # topo do estilo B
FACE_OUT = ROOT / "art/tiles/plateau_a_face.png"
BLOCK = (204, 498, 563, 680)   # bloco de paredão 4x2 células, por dentro da borda da grade
# Linhas internas da grade (coordenadas da cartela, fim exclusivo), medidas pela cor: a
# grade é cinza e a pedra é marrom.
GRID_COLS = [(290, 295), (382, 386), (473, 478)]
GRID_ROWS = [(591, 595)]
CELLS = (4, 2)
PALETTE = 20
T = 32
ROWS = 3
VARIANTS = 4
TOP_Y = 14                     # linha do tile onde a pedra começa (a grama cobre o começo)
HEIGHT = 46                    # altura do paredão (~1,4 tile)
SHADOW_ROWS = 3
SHADOW = (20, 36, 14)
GROUND = (86, 128, 52)          # base da grama de baixo (tile cheio de art/tiles/grass.png)
BLADE = [(59, 95, 49), (72, 110, 50), (87, 128, 54), (110, 150, 56), (127, 169, 57), (150, 190, 72)]
SIDE_W = 4
ATLAS_BY_MASK = [
    (0, 3), (1, 3), (0, 0), (3, 0), (0, 2), (1, 0), (2, 3), (1, 1),
    (3, 3), (0, 1), (3, 2), (2, 0), (1, 2), (2, 2), (3, 1), (2, 1),
]


def _lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rock_strip() -> Image.Image:
    """Bloco da cartela sem as linhas da grade, em 32 px por célula, com paleta limitada."""
    sheet = Image.open(SHEET).convert("RGB")
    sp = sheet.load()
    # Tira a grade: cada faixa de linha vira a interpolação entre os pixels dos dois lados.
    for x0, x1 in GRID_COLS:
        for y in range(BLOCK[1], BLOCK[3]):
            left, right = sp[x0 - 1, y], sp[x1, y]
            for x in range(x0, x1):
                sp[x, y] = _lerp(left, right, (x - x0 + 1) / (x1 - x0 + 1))
    for y0, y1 in GRID_ROWS:
        for x in range(BLOCK[0], BLOCK[2]):
            top, bottom = sp[x, y0 - 1], sp[x, y1]
            for y in range(y0, y1):
                sp[x, y] = _lerp(top, bottom, (y - y0 + 1) / (y1 - y0 + 1))
    block = sheet.crop(BLOCK)
    small = block.resize((CELLS[0] * T, CELLS[1] * T), Image.BOX)
    return small.quantize(colors=PALETTE, method=Image.Quantize.MEDIANCUT).convert("RGB")


def edge_rows(grass, tx: int, ty: int) -> list[int | None]:
    """Última linha de grama (pixel verde) de cada coluna, se a grama termina na peça."""
    out: list[int | None] = []
    for x in range(T):
        ys = [y for y in range(T) if is_green(grass[tx * T + x, ty * T + y])]
        out.append(None if not ys or ys[-1] >= T - 2 else ys[-1])
    return out


def is_green(p: tuple) -> bool:
    return p[3] > 0 and p[1] > p[0] + 5


def blades() -> tuple[list[int], list[int]]:
    rng = random.Random(23)
    hs, ss = [], []
    for x in range(T):
        v = 1.4 + 1.2 * math.sin(x * 0.75 + 0.4) + 0.8 * math.sin(x * 2.1 + 1.0) + rng.uniform(-0.8, 0.8)
        hs.append(max(0, min(3, round(v))))
        ss.append(rng.randint(1, SHADOW_ROWS))
    return hs, ss


def build() -> None:
    strip = rock_strip()
    sp = strip.load()
    grass = Image.open(GRASS).convert("RGBA")
    alpha = grass.load()
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
                d = min((abs(x - e) for e in ends), default=99)
                cut = {0: 5, 1: 3, 2: 1}.get(d, 0)  # ponta arredondada
                start = max(TOP_Y, rows[x] - 1)
                base = TOP_Y + HEIGHT - cut
                for y in range(start, base):
                    c = sp[v * T + x, min(strip.height - 1, y - TOP_Y)]
                    if base - y <= 3:
                        c = tuple(round(k * (0.92 - 0.05 * (3 - (base - y)))) for k in c)
                    fp[ox + x, oy + y] = c + (255,)
                fp[ox + x, oy + base] = GROUND + (255,)
                for k in range(1, 1 + ss[x]):
                    if base + k < ROWS * T:
                        fp[ox + x, oy + base + k] = SHADOW + (int(70 * (1 - (k - 1) / SHADOW_ROWS)),)
                for k in range(hs[x] + 1):
                    t = k / max(1, hs[x])
                    fp[ox + x, oy + base - k] = BLADE[min(len(BLADE) - 2, round(t * (len(BLADE) - 2)))] + (255,)
    face.save(FACE_OUT)

    print(f"salvo em {FACE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
