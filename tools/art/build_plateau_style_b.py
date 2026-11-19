"""Estilo B do planalto: tileset de 16 peças com o barranco de pedra já desenhado.

    python tools/art/build_plateau_style_b.py

Entrada: art/source/cliff_grass_b_2x.png (o tileset enviado, ampliado 2x sem perda).
Saídas:
  art/tiles/cliff_grass_b.png   32 px por tile, layout de cantos de art/tiles/grass.png
  art/tiles/plateau_b_face.png  continuação do paredão abaixo das peças com borda sul: um
                                tile alto (32 x ROWS*32) por máscara, no layout de
                                DualGrid.ATLAS_BY_MASK com a linha multiplicada por ROWS
  art/tiles/plateau_b_rim.png   atlas 4x4: pedrinhas soltas nas laterais e no norte

A grama segue o layout da grama do jogo, mas o autor guardou a parte de baixo do paredão
em peças sem borda sul (a peça "vazia" tem a base na metade direita, a de "só o canto de
baixo à direita" na metade esquerda). No dual grid essas peças aparecem nos cantos de cima
e nas laterais, então a pedra sai delas e vira o atlas do paredão: abaixo de cada coluna
com borda sul vem um trecho do meio da pedra repetido (MID, para ficar mais alto), a base
original e, no pé, tufos de grama e sombra suave para ligar com o chão.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art/source/cliff_grass_b_2x.png"
OUT = ROOT / "art/tiles/cliff_grass_b.png"
FACE_OUT = ROOT / "art/tiles/plateau_b_face.png"
RIM_OUT = ROOT / "art/tiles/plateau_b_rim.png"
SIDE_W = 10                # faixa de pedrinhas nas laterais
TAPER = 6                  # na quina com o paredão, a faixa afina nesses últimos px
NORTH_W = 7                # e no norte
# Pedrinhas soltas (referência enviada pelo usuário): bege com luz em cima, frestas marrons.
PEBBLE = [(118, 84, 62), (150, 116, 84), (172, 146, 102), (198, 182, 136)]  # fresta -> brilho
PEBBLE_EDGE = (92, 64, 48)    # contorno de fora
PEBBLE_CELLS = 14             # pedrinhas por peça (padrão que repete a cada 32 px)
T = 32
ROWS = 2
# Peças (coluna, linha) cujos cantos não têm borda sul mas vieram com pedra.
NO_SOUTH_WITH_ROCK = [(3, 2), (1, 3), (0, 3)]
STRAIGHT = (1, 2)          # borda sul reta: fonte do trecho do meio
BASE_LEFT = (1, 3)         # base do paredão, metade esquerda
BASE_RIGHT = (0, 3)        # base do paredão, metade direita
# Trecho do meio (linhas da peça de borda sul reta) repetido para ficar mais alto. Ele
# começa numa faixa clara (topo dos blocos); para essa faixa não virar uma linha reta no
# limite entre os tiles, cada coluna começa 0 a JAG_MAX px mais abaixo (as primeiras linhas
# viram a pedra escura do fim da peça), como o começo irregular da primeira faixa.
MID = [(22, 32)]
JAG_MAX = 3
SHADOW_ROWS = 4
SHADOW = (20, 36, 14)
GROUND = (86, 128, 52)          # base da grama de baixo (tile cheio de art/tiles/grass.png)
BLADE = [(59, 95, 49), (72, 110, 50), (87, 128, 54), (110, 150, 56), (127, 169, 57), (150, 190, 72)]
ATLAS_BY_MASK = [
    (0, 3), (1, 3), (0, 0), (3, 0), (0, 2), (1, 0), (2, 3), (1, 1),
    (3, 3), (0, 1), (3, 2), (2, 0), (1, 2), (2, 2), (3, 1), (2, 1),
]


def is_rock(p: tuple) -> bool:
    return p[3] > 0 and p[0] > p[1] + 5


def jag(x: int) -> int:
    """Quantas linhas do começo do trecho do meio viram pedra escura nesta coluna."""
    v = 1.2 + 1.1 * math.sin(x * 0.85 + 0.3) + 0.7 * math.sin(x * 2.4 + 1.1)
    return max(0, min(JAG_MAX, round(v)))


def is_grass(p: tuple) -> bool:
    return p[3] > 0 and not is_rock(p)


def _pebbles() -> tuple[list[tuple[float, float]], list[float]]:
    rng = random.Random(41)
    pts = [(rng.uniform(0, T), rng.uniform(0, T)) for _ in range(PEBBLE_CELLS)]
    tone = [rng.uniform(-0.25, 0.25) for _ in range(PEBBLE_CELLS)]
    return pts, tone


def _nearest(pts: list[tuple[float, float]], x: float, y: float) -> tuple[int, float, float, float, float]:
    """Pedrinha mais próxima no padrão periódico: índice, distâncias d1 e d2 e o centro
    (na cópia do padrão mais perto do pixel)."""
    best: list[tuple[float, int, float, float]] = []
    for i, (px_, py_) in enumerate(pts):
        dx = (x - px_ + T / 2) % T - T / 2
        dy = (y - py_ + T / 2) % T - T / 2
        best.append((math.hypot(dx, dy), i, x - dx, y - dy))
    best.sort()
    (d1, i, cx, cy), (d2, _, _, _) = best[0], best[1]
    return i, d1, d2, cx, cy


def build_rim(px) -> None:
    """Pedrinhas soltas fora da grama: até SIDE_W px nas laterais e NORTH_W no norte. No sul
    o tileset já tem a pedra (e o paredão continua embaixo). O padrão das pedrinhas repete a
    cada 32 px, então emenda entre as peças; uma pedrinha entra inteira se o centro dela
    está na faixa (a borda de fora fica irregular, seguindo as pedras)."""
    pts, tone = _pebbles()
    rim = Image.new("RGBA", (4 * T, 4 * T), (0, 0, 0, 0))
    rp = rim.load()
    for ty in range(4):
        for tx in range(4):
            def grass(x: int, y: int) -> bool:
                return 0 <= x < T and 0 <= y < T and is_grass(px[tx * T + x, ty * T + y])

            def side_width(gx: int, y: int) -> float:
                """Largura da faixa lateral na linha y, junto à coluna de grama gx. Na
                quina com a borda sul (a grama dessa coluna termina dentro da peça), a
                faixa afina nos últimos TAPER px até encontrar o paredão, senão sobra
                um toco de pedrinhas ao lado dele."""
                rows = [yy for yy in range(T) if grass(gx, yy)]
                if not rows or rows[-1] >= T - 2:
                    return SIDE_W
                return SIDE_W * min(1.0, max(0.0, (rows[-1] - y + 1) / TAPER))

            def band_dist(x: int, y: int) -> int:
                """Distância até a grama pela lateral ou pelo norte (0 = grama; 99 = longe
                ou só pelo sul)."""
                if grass(x, y):
                    return 0
                dw = next((k for k in range(1, SIDE_W + 2) if grass(x + k, y)), 99)
                de = next((k for k in range(1, SIDE_W + 2) if grass(x - k, y)), 99)
                dn = next((k for k in range(1, NORTH_W + 2) if grass(x, y + k)), 99)
                side = min(dw, de)
                if side <= SIDE_W and side <= side_width(x + (dw if dw <= de else -de), y):
                    return side
                return dn if dn <= NORTH_W else 99

            for y in range(T):
                for x in range(T):
                    if px[tx * T + x, ty * T + y][3] > 0:
                        continue  # grama ou pedra do próprio tileset
                    if band_dist(x, y) > max(SIDE_W, NORTH_W) + 2:
                        continue
                    i, d1, d2, cx, cy = _nearest(pts, x + 0.5, y + 0.5)
                    ccx, ccy = int(math.floor(cx)), int(math.floor(cy))
                    if 0 <= ccx < T and 0 <= ccy < T:
                        if band_dist(ccx, ccy) == 99:
                            continue  # pedrinha de fora da faixa
                    elif band_dist(x, y) > SIDE_W - 1:
                        continue
                    if d2 - d1 < 1.6:
                        c = PEBBLE[0]                      # fresta entre pedrinhas
                    else:
                        r = max(1.0, d1)
                        light = -((x + 0.5 - cx) * 0.6 + (y + 0.5 - cy) * 0.8) / max(2.5, r + 1.5) + tone[i]
                        c = PEBBLE[3] if light > 0.3 else PEBBLE[2] if light > -0.1 else PEBBLE[1] if light > -0.4 else PEBBLE[0]
                    rp[tx * T + x, ty * T + y] = c + (255,)
            # Contorno de fora: pixel vazio colado numa pedrinha, fora da grama.
            for y in range(T):
                for x in range(T):
                    if rp[tx * T + x, ty * T + y][3] or px[tx * T + x, ty * T + y][3]:
                        continue
                    if any(0 <= x + dx < T and 0 <= y + dy < T and rp[tx * T + x + dx, ty * T + y + dy][3] == 255
                           and rp[tx * T + x + dx, ty * T + y + dy][:3] != PEBBLE_EDGE
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        if band_dist(x, y) <= max(SIDE_W, NORTH_W) + 1:
                            rp[tx * T + x, ty * T + y] = PEBBLE_EDGE + (200,)
    rim.save(RIM_OUT)


WRAP_REACH = 7   # até quantos px da ponta do paredão a dobra do canto é estendida


def extend_corner_wraps(px, fp, ax: int, ay: int, ox: int, oy: int, mid, base, hs, ss) -> None:
    """Nos cantos de fora, a pedra da peça dobra a esquina e desce um pouco pela lateral,
    mas termina antes do fim da peça; sem continuação ela fica solta ao lado do paredão
    (nos degraus da borda isso aparece como um toco de pedra). Estas colunas descem do
    fim da pedra da peça até a mesma base das colunas vizinhas do paredão, com a coluna de
    fora mais escura e o pé arredondado, como a ponta de um paredão."""
    def has_face(x: int) -> bool:
        return 0 <= x < T and fp[ox + x, oy + T][3] == 255

    def face_bottom(x: int) -> int:
        y = T
        while y < ROWS * T and fp[ox + x, oy + y][3] == 255 and fp[ox + x, oy + y][:3] != GROUND:
            y += 1
        return y

    faced = [x for x in range(T) if has_face(x)]
    if not faced:
        return
    for x in range(T):
        if has_face(x):
            continue
        rocks = [y for y in range(T // 2, T) if is_rock(px[ax * T + x, ay * T + y])]
        if not rocks:
            continue
        nearest = min(faced, key=lambda f: abs(f - x))
        dist = abs(nearest - x)
        if dist > WRAP_REACH:
            continue
        start = rocks[-1] + 1
        bottom = face_bottom(nearest) - {1: 0, 2: 1, 3: 1}.get(dist, 2)   # pé arredondado
        column = list(mid[x]) + list(base[x] or base[nearest])
        length = bottom - start
        if length <= 0:
            continue
        pixels = [p for p in column if is_rock(p)][-length:]
        shade = 0.72 if dist == WRAP_REACH or not has_face(x + (1 if x < nearest else -1) * -1) and dist > 1 else 1.0
        y = bottom - len(pixels)
        for p in pixels:
            c = tuple(round(v * shade) for v in p[:3])
            fp[ox + x, oy + y] = c + (255,)
            y += 1
        if bottom < ROWS * T:
            fp[ox + x, oy + bottom] = GROUND + (255,)
        for k in range(1, 1 + ss[x]):
            if bottom + k < ROWS * T and fp[ox + x, oy + bottom + k][3] == 0:
                fp[ox + x, oy + bottom + k] = SHADOW + (int(80 * (1 - (k - 1) / SHADOW_ROWS)),)
        for k in range(min(hs[x], 2) + 1):
            t = k / max(1, hs[x])
            if 0 <= bottom - k < ROWS * T:
                fp[ox + x, oy + bottom - k] = BLADE[min(len(BLADE) - 2, round(t * (len(BLADE) - 2)))] + (255,)


def blades() -> tuple[list[int], list[int]]:
    rng = random.Random(31)
    hs, ss = [], []
    for x in range(T):
        v = 1.6 + 1.2 * math.sin(x * 0.7 + 0.9) + 0.8 * math.sin(x * 2.2 + 0.2) + rng.uniform(-0.8, 0.8)
        hs.append(max(0, min(4, round(v))))
        ss.append(rng.randint(2, SHADOW_ROWS))
    return hs, ss


def build() -> None:
    src = Image.open(SOURCE).convert("RGBA")
    original = src.resize((src.width // 2, src.height // 2), Image.NEAREST)
    op = original.load()
    img = original.copy()
    px = img.load()
    for tx, ty in NO_SOUTH_WITH_ROCK:
        for y in range(T):
            for x in range(T):
                if is_rock(px[tx * T + x, ty * T + y]):
                    px[tx * T + x, ty * T + y] = (0, 0, 0, 0)
    img.save(OUT)

    # Base de cada coluna: a pedra das peças limpas (antes de limpar), do topo para baixo.
    base: list[list[tuple]] = []
    for x in range(T):
        tx, ty = BASE_LEFT if x < T // 2 else BASE_RIGHT
        col: list[tuple] = []
        for y in range(T):
            p = op[tx * T + x, ty * T + y]
            if not is_rock(p):
                break
            col.append(p)
        base.append(col)
    sx, sy = STRAIGHT
    mid = [[op[sx * T + x, sy * T + y] for a, b in MID for y in range(a, b)] for x in range(T)]
    hs, ss = blades()

    face = Image.new("RGBA", (4 * T, 4 * T * ROWS), (0, 0, 0, 0))
    fp = face.load()
    for mask in range(16):
        tl, tr, bl, br = bool(mask & 8), bool(mask & 4), bool(mask & 2), bool(mask & 1)
        if not ((tl and not bl) or (tr and not br)):
            continue
        ax, ay = ATLAS_BY_MASK[mask]
        ox, oy = ax * T, ay * T * ROWS
        for x in range(T):
            south = (x < T // 2 and tl and not bl) or (x >= T // 2 and tr and not br)
            # Só onde a pedra da peça chega no fim do tile (ela continua para baixo).
            if not south or not is_rock(px[ax * T + x, ay * T + T - 1]):
                continue
            y = T
            n = jag(x)
            last_rows = [op[sx * T + x, sy * T + T - 1 - k] for k in range(JAG_MAX)]
            for j, p in enumerate(mid[x]):
                if j < n:
                    p = last_rows[n - 1 - j]  # começo irregular: pedra escura do fim da peça
                if is_rock(p):
                    fp[ox + x, oy + y] = p
                y += 1
            col = base[x] or base[min(range(T), key=lambda k: abs(k - x) if base[k] else 99)]
            for p in col:
                fp[ox + x, oy + y] = p
                y += 1
            bottom = y  # primeira linha de chão
            if bottom < ROWS * T:
                fp[ox + x, oy + bottom] = GROUND + (255,)
            for k in range(1, 1 + ss[x]):
                if bottom + k < ROWS * T:
                    fp[ox + x, oy + bottom + k] = SHADOW + (int(80 * (1 - (k - 1) / SHADOW_ROWS)),)
            for k in range(hs[x] + 1):
                t = k / max(1, hs[x])
                if 0 <= bottom - k < ROWS * T:
                    fp[ox + x, oy + bottom - k] = BLADE[min(len(BLADE) - 2, round(t * (len(BLADE) - 2)))] + (255,)
        extend_corner_wraps(px, fp, ax, ay, ox, oy, mid, base, hs, ss)
    face.save(FACE_OUT)
    build_rim(px)
    print(f"salvo em {OUT.relative_to(ROOT)}, {FACE_OUT.relative_to(ROOT)} e {RIM_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
