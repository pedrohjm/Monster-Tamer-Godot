"""Gera a borda de pedra e o paredão sul dos planaltos (GAME_DESIGN §7.1.1).

    python tools/art/build_plateau_ridge.py

Saídas:
  art/tiles/plateau_top.png    atlas 4x4: a grama do topo cortada para dentro da borda de pedra
                               (a beirada da grama não vaza para fora da pedra)
  art/tiles/plateau_ridge.png  atlas 4x4 de cantos (layout de art/tiles/grass.png): borda de
                               pedra desenhada POR CIMA da grama do topo
  art/tiles/plateau_face.png   paredão abaixo das bordas sul: um tile alto (32 x ROWS*32) por
                               máscara, no layout de DualGrid.ATLAS_BY_MASK com a linha
                               multiplicada por ROWS (ver DualGridTerrain.face_source_id)

Estilo: vem do tileset de pedra art/tiles/stone.png. De cada peça tiramos só a borda (até
BAND px da borda transparente; o miolo liso fica transparente para a grama do topo
aparecer). Os blocos de pedra viram os marrons do bioma; a poeira clara de fora (que no
tileset era chão de pedra) sai: a grama de baixo encosta direto na pedra, só com uma sombra
de contato. No sul, os blocos continuam para baixo por FACE_H px e terminam em tufos de
grama de alturas variadas, nos tons da grama de baixo, subindo por cima da pedra.
"""
from __future__ import annotations

import collections
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art/tiles/stone.png"
GRASS = ROOT / "art/tiles/grass.png"
TOP_OUT = ROOT / "art/tiles/plateau_top.png"
RIDGE_OUT = ROOT / "art/tiles/plateau_ridge.png"
FACE_OUT = ROOT / "art/tiles/plateau_face.png"
T = 32
ROWS = 2
BAND = 16            # largura da borda de pedra (medida no tileset de pedra)
SOFT = 12            # a partir daqui, pixels claros (miolo liso) também saem
FLOOR_LUM = (88, 114)  # brilho do chão liso do tileset (blocos: 36-70 escuro, 124+ brilho)
RIM = 5              # pixels de fora da borda (contorno + poeira) que viram franja de grama
ROCK_ROWS = (6, 15)  # faixa de blocos (distância da borda) repetida no paredão sul
FACE_H = 18          # quanto o paredão sul desce além da borda
SHADOW_ROWS = 3
SHADOW = (20, 36, 14)
CONTACT = (24, 40, 18, 110)     # sombra de 1 px onde a pedra encosta na grama de baixo
CAST = (5, 5)                   # sombra projetada (luz de cima à esquerda): deslocamento
CAST_COLOR = (16, 30, 12)
CAST_ALPHA = 72
GROUND = (86, 128, 52)          # base da grama de baixo (tile cheio de art/tiles/grass.png)
BLADE = [(59, 95, 49), (72, 110, 50), (87, 128, 54), (110, 150, 56), (127, 169, 57), (150, 190, 72)]
BLADE_MAX = 3                   # tufos só no pé do paredão
POCKET = (66, 42, 32)           # chão liso preso entre os blocos -> pedra escura
STRAIGHT = (1, 2)    # peça com a borda sul reta: fonte da textura do paredão

# Brilho (0..255) -> cor. Blocos de pedra: marrons quentes, como a terra.
ROCK_RAMP = [
    (0, (24, 14, 12)), (45, (52, 32, 26)), (70, (80, 52, 38)), (95, (116, 80, 54)),
    (120, (152, 112, 76)), (150, (188, 150, 104)), (200, (222, 194, 146)),
]
# Franja: os verdes da borda do tileset de grama.
GRASS_RAMP = [
    (0, (30, 50, 26)), (66, (48, 80, 41)), (79, (59, 95, 49)), (106, (87, 128, 54)),
    (144, (127, 169, 57)), (200, (160, 196, 80)),
]
ATLAS_BY_MASK = [
    (0, 3), (1, 3), (0, 0), (3, 0), (0, 2), (1, 0), (2, 3), (1, 1),
    (3, 3), (0, 1), (3, 2), (2, 0), (1, 2), (2, 2), (3, 1), (2, 1),
]


def lum(rgb: tuple) -> float:
    return (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000


def is_floor(p: tuple) -> bool:
    """Se o pixel é do chão liso do tileset de pedra (não um bloco)."""
    return FLOOR_LUM[0] <= lum(p) <= FLOOR_LUM[1]


def ramp(rgb: tuple, table: list) -> tuple[int, int, int]:
    v = lum(rgb)
    for (l0, c0), (l1, c1) in zip(table, table[1:]):
        if v <= l1:
            t = (v - l0) / (l1 - l0)
            return tuple(round(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))  # type: ignore[return-value]
    return table[-1][1]


def distance_to_empty(px, tx: int, ty: int) -> list[list[int]]:
    """Distância (4 vizinhos) até o pixel transparente mais próximo dentro da peça. Fora
    da peça conta como cheio: no dual grid a forma sempre continua no vizinho."""
    far = 99
    d = [[far] * T for _ in range(T)]
    q: collections.deque[tuple[int, int]] = collections.deque()
    for y in range(T):
        for x in range(T):
            if px[tx * T + x, ty * T + y][3] == 0:
                d[y][x] = 0
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < T and 0 <= ny < T and d[ny][nx] > d[y][x] + 1:
                d[ny][nx] = d[y][x] + 1
                q.append((nx, ny))
    return d


def south_columns(sp, tx: int, ty: int, mask: int, d: list[list[int]]) -> dict[int, int]:
    """Colunas da peça com borda sul (e pedra visível) -> última linha opaca da forma."""
    tl, tr, bl, br = bool(mask & 8), bool(mask & 4), bool(mask & 2), bool(mask & 1)
    out: dict[int, int] = {}
    for x in range(T):
        if not ((x < T // 2 and tl and not bl) or (x >= T // 2 and tr and not br)):
            continue
        ys = [y for y in range(T) if sp[tx * T + x, ty * T + y][3] > 0]
        if not ys or ys[-1] >= T - 2:
            continue
        # Coluna só com a poeira de fora (removida da borda): sem pedra visível acima, o
        # paredão sairia para fora da borda lateral nas pontas.
        if not any(d[y][x] > RIM for y in ys):
            continue
        out[x] = ys[-1]
    return out


def _interior(sp, tx: int, ty: int, d: list[list[int]]) -> set[tuple[int, int]]:
    """Pixels do miolo liso: os de distância > BAND e os claros (chão liso) a partir de
    SOFT que se ligam a eles. Chão liso preso entre os blocos não conta (senão vira
    buraco na borda)."""
    inside: set[tuple[int, int]] = set()
    q: collections.deque[tuple[int, int]] = collections.deque()
    for y in range(T):
        for x in range(T):
            if sp[tx * T + x, ty * T + y][3] and d[y][x] > BAND:
                inside.add((x, y))
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < T and 0 <= ny < T) or (nx, ny) in inside:
                continue
            p = sp[tx * T + nx, ty * T + ny]
            if p[3] and d[ny][nx] >= SOFT and is_floor(p):
                inside.add((nx, ny))
                q.append((nx, ny))
    return inside


def _blades() -> tuple[list[int], list[int], list[bool]]:
    """Altura do tufo, comprimento da sombra e ponta clara de cada coluna (0..T-1): ondas
    somadas com um pouco de sorteio, para formar touceiras e não uma régua."""
    import math
    import random
    rng = random.Random(17)
    heights, shadows, tips = [], [], []
    for x in range(T):
        v = 1.4 + 1.2 * math.sin(x * 0.75 + 1.3) + 0.8 * math.sin(x * 2.3 + 0.4) + rng.uniform(-0.8, 0.8)
        heights.append(max(0, min(BLADE_MAX, round(v))))
        shadows.append(rng.randint(1, SHADOW_ROWS))
        tips.append(rng.random() < 0.45)
    return heights, shadows, tips


BLADE_H, BLADE_SHADOW, BLADE_TIP = _blades()


def add_cast_shadow(rp, tp, fp) -> None:
    """Sombra projetada no chão de baixo, para a direita e para baixo: a silhueta do
    planalto (topo + borda + paredão) deslocada em CAST, fora da própria silhueta. Vai no
    atlas do paredão (tiles de ROWS células) para todas as máscaras parciais. Como o
    paredão é desenhado por cima do topo, a sombra não pode cair onde a forma continua no
    tile vizinho (no dual grid, onde a forma toca a lateral da peça ela segue no vizinho)."""
    for mask in range(1, 15):
        tx, ty = ATLAS_BY_MASK[mask]
        ox, oy = tx * T, ty * T * ROWS
        h = T * ROWS
        solid = [[False] * T for _ in range(h)]
        for y in range(h):
            for x in range(T):
                if fp[ox + x, oy + y][3] == 255:
                    solid[y][x] = True
                elif y < T and (rp[tx * T + x, ty * T + y][3] == 255 or tp[tx * T + x, ty * T + y][3] > 0):
                    solid[y][x] = True
        # Na segunda célula (o tile de baixo), onde a forma chega no fim desta peça ela
        # continua no vizinho: conta como cheio (o paredão é desenhado por cima do topo,
        # então a sombra ali apareceria em cima do planalto).
        blocked = [row[:] for row in solid]  # recebe sombra? (só a silhueta real projeta)
        for x in range(T):
            if solid[T - 1][x]:
                for y in range(T, h):
                    blocked[y][x] = True
        sx, sy = CAST
        for y in range(h):
            for x in range(T):
                if blocked[y][x]:
                    continue
                src_x, src_y = x - sx, y - sy
                if not (0 <= src_y < h):
                    continue
                if src_x < 0:
                    # a forma continua no tile da esquerda se toca a lateral nessa linha
                    if not solid[src_y][0]:
                        continue
                elif not solid[src_y][src_x]:
                    continue
                old = fp[ox + x, oy + y]
                if old[3] < CAST_ALPHA:
                    fp[ox + x, oy + y] = CAST_COLOR + (CAST_ALPHA,)


def build() -> None:
    src = Image.open(SOURCE).convert("RGBA")
    sp = src.load()
    ridge = Image.new("RGBA", src.size, (0, 0, 0, 0))
    rp = ridge.load()
    face = Image.new("RGBA", (4 * T, 4 * T * ROWS), (0, 0, 0, 0))
    fp = face.load()

    # Textura do paredão: a faixa de blocos da peça de borda sul reta, coluna a coluna.
    sx, sy = STRAIGHT
    sd = distance_to_empty(sp, sx, sy)
    straight_south = south_columns(sp, sx, sy, 12, sd)
    rock_tex: dict[int, list[tuple]] = {}
    for x, edge in straight_south.items():
        rock_tex[x] = [sp[sx * T + x, sy * T + y] for y in range(edge - ROCK_ROWS[1], edge - ROCK_ROWS[0] + 1)]

    grass = Image.open(GRASS).convert("RGBA")
    gp = grass.load()
    top = Image.new("RGBA", src.size, (0, 0, 0, 0))
    tp = top.load()
    for mask in range(16):
        tx, ty = ATLAS_BY_MASK[mask]
        d = distance_to_empty(sp, tx, ty)
        south = south_columns(sp, tx, ty, mask, d)
        interior = _interior(sp, tx, ty, d)
        rock: set[tuple[int, int]] = set()
        for y in range(T):
            for x in range(T):
                gx, gy = tx * T + x, ty * T + y
                p = sp[gx, gy]
                if p[3] and d[y][x] > RIM:
                    tp[gx, gy] = gp[gx, gy]  # grama do topo só dentro da borda
                if p[3] == 0 or (x, y) in interior:
                    continue  # miolo liso: a grama do topo aparece
                dist = d[y][x]
                if dist <= RIM:
                    continue  # poeira de fora: sai (a grama de baixo encosta na pedra)
                if is_floor(p):
                    # chão liso preso entre os blocos: vira pedra escura (sem buraco)
                    rp[gx, gy] = POCKET + (255,)
                else:
                    rp[gx, gy] = ramp(p[:3], ROCK_RAMP) + (255,)
                rock.add((x, y))
        # Sombra de contato: 1 px fora da pedra, menos no sul (lá entra o paredão).
        for x, y in rock:
            for dx, dy in ((1, 0), (-1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < T and 0 <= ny < T) or (nx, ny) in rock:
                    continue
                if d[ny][nx] > RIM or (nx in south and ny > south[nx] - RIM):
                    continue
                if rp[tx * T + nx, ty * T + ny][3] == 0:
                    rp[tx * T + nx, ty * T + ny] = CONTACT
        if not south:
            continue
        # Canto interno: entre a ponta do paredão e a borda lateral do braço vizinho do
        # planalto sobra a faixa onde era a poeira (sem pedra). O paredão continua de lado
        # até encostar na pedra, senão aparece grama no meio do canto.
        face_cols = dict(south)
        for e in south:
            for step in (-1, 1):
                if (e + step) in south:
                    continue  # não é ponta
                x = e + step
                rows = range(south[e] - RIM + 1, south[e] + 1)
                while 0 <= x < T and x not in south and abs(x - e) <= RIM + 2:
                    if not any(sp[tx * T + x, ty * T + y][3] for y in rows if 0 <= y < T):
                        break  # fora da forma: ponta de verdade, não canto interno
                    if any(rp[tx * T + x, ty * T + y][3] == 255 for y in rows if 0 <= y < T):
                        break  # chegou na pedra da borda lateral
                    face_cols[x] = south[e]
                    x += step
        # Paredão: blocos continuam para baixo e terminam em tufos de grama.
        ox, oy = tx * T, ty * T * ROWS
        for x, edge in face_cols.items():
            tex = rock_tex.get(x) or rock_tex[min(rock_tex, key=lambda k: abs(k - x))]
            alt = rock_tex.get((x + 11) % T) or tex   # segunda volta com outra coluna
            # Começa mais acima onde não há pedra da borda por cima (vértice do canto
            # interno), senão sobra um triângulo de grama.
            start = edge - RIM + 1
            while (start - 1 >= 0 and sp[tx * T + x, ty * T + start - 1][3]
                   and d[start - 1][x] <= RIM and rp[tx * T + x, ty * T + start - 1][3] != 255):
                start -= 1
            for k in range(start - (edge - RIM + 1), 0):
                src_px = tex[k % len(tex)]
                c = POCKET if is_floor(src_px) else ramp(src_px[:3], ROCK_RAMP)
                fp[ox + x, oy + edge - RIM + 1 + k] = c + (255,)
            y = edge - RIM + 1
            for k in range(FACE_H):
                col = tex if k < len(tex) else alt
                src_px = col[k % len(col)]
                c = POCKET if is_floor(src_px) else ramp(src_px[:3], ROCK_RAMP)
                if k >= FACE_H - 4:
                    c = tuple(round(v * (0.9 - 0.04 * (k - FACE_H + 4))) for v in c)  # escurece no pé
                fp[ox + x, oy + y] = c + (255,)
                y += 1
            base = y  # primeira linha de chão
            fp[ox + x, oy + base] = GROUND + (255,)
            # Sombra irregular no chão.
            for k in range(1, 1 + BLADE_SHADOW[x]):
                if base + k < ROWS * T:
                    fp[ox + x, oy + base + k] = SHADOW + (int(70 * (1 - (k - 1) / SHADOW_ROWS)),)
            # Tufo: lâmina de altura variada subindo por cima da pedra, escura embaixo e
            # clara na ponta.
            h = BLADE_H[x]
            for k in range(h + 1):
                t = k / max(1, h)
                idx = min(len(BLADE) - 2, round(t * (len(BLADE) - 2)))
                if k == h and h >= 2 and BLADE_TIP[x]:
                    idx = len(BLADE) - 1
                fp[ox + x, oy + base - k] = BLADE[idx] + (255,)
        # Frestas de até 3 px entre pedra (borda ou paredão) nos dois lados, na altura do
        # paredão: viram pedra escura (fiozinho de grama nos cantos internos).
        top_row = min(edge - RIM + 1 for edge in face_cols.values()) - RIM
        bottom_row = max(edge - RIM + 1 for edge in face_cols.values()) + FACE_H
        for y in range(max(0, top_row), min(T, bottom_row)):
            solid = [fp[ox + x, oy + y][3] == 255 or rp[tx * T + x, ty * T + y][3] == 255 for x in range(T)]
            x = 0
            while x < T:
                if solid[x]:
                    x += 1
                    continue
                run = x
                while run < T and not solid[run]:
                    run += 1
                if x > 0 and run < T and run - x <= 3:
                    for gx in range(x, run):
                        fp[ox + gx, oy + y] = POCKET + (255,)
                x = run
    add_cast_shadow(rp, tp, fp)
    top.save(TOP_OUT)
    ridge.save(RIDGE_OUT)
    face.save(FACE_OUT)
    print(f"salvo em {TOP_OUT.relative_to(ROOT)}, {RIDGE_OUT.relative_to(ROOT)} e {FACE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
