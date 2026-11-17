"""Gera variações do tile cheio de grama: art/tiles/grass_variants.png (uma fileira de 32x32).

    python tools/art/build_grass_variants.py

Parte do tile cheio de art/tiles/grass.png (coluna 2, linha 1 do atlas 4x4). Mantém uma
moldura de RING px igual ao original, para emendar com qualquer vizinho, e refaz o miolo:
  - "mistura": tira os enfeites (trevos, folhinhas) e espalha os mesmos enfeites em
    outras posições, para a repetição do tile não formar grade;
  - "flores": mistura + um punhado de florzinhas (GAME_DESIGN §8: trevo e florzinhas em
    ~10–15% das células, no mesmo tom da base).
A ordem das variações aqui é a ordem das colunas no PNG (usada em build_grass_tileset.gd).
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "art/tiles/grass.png"
OUT = ROOT / "art/tiles/grass_variants.png"
T = 32
FULL = (2, 1)
RING = 2
BASE_TOLERANCE = 9  # distância de cor até a qual o pixel conta como chão liso

# (nome, semente, fração dos enfeites originais, flores: (cor, quantidade) ou None)
VARIANTS = [
    ("mistura_a", 11, 1.0, None),
    ("mistura_b", 23, 1.2, None),
    ("calma", 37, 0.5, None),
    ("flores_brancas", 41, 0.8, ("branca", 4)),
    ("flores_amarelas", 53, 0.8, ("amarela", 4)),
    ("flores_rosas", 67, 0.8, ("rosa", 3)),
]

# pétala, sombra da pétala, miolo
FLOWER_COLORS = {
    "branca": ((236, 234, 214), (190, 196, 160), (232, 196, 74)),
    "amarela": ((236, 204, 72), (186, 150, 44), (150, 100, 34)),
    "rosa": ((226, 140, 172), (176, 96, 132), (240, 220, 140)),
}
FLOWER_SHADOW = (61, 99, 48)  # verde escuro dos trevos, embaixo da flor


def dist(a: tuple, b: tuple) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def main() -> None:
    atlas = Image.open(ATLAS).convert("RGBA")
    full = atlas.crop((FULL[0] * T, FULL[1] * T, FULL[0] * T + T, FULL[1] * T + T))
    px = full.load()
    counts = sorted(full.getcolors(4096), reverse=True)
    base = counts[0][1]
    base_noise = [c for n, c in counts if dist(c, base) <= BASE_TOLERANCE for _ in range(min(n, 40))]

    is_deco = [[dist(px[x, y], base) > BASE_TOLERANCE for x in range(T)] for y in range(T)]
    stamps = extract_stamps(px, is_deco)

    out = Image.new("RGBA", (T * len(VARIANTS), T))
    for i, (name, seed, density, flowers) in enumerate(VARIANTS):
        rng = random.Random(seed)
        tile = full.copy()
        tp = tile.load()
        occupied = [[False] * T for _ in range(T)]
        # Limpa o miolo, mantendo a moldura e os enfeites que encostam nela.
        for y in range(RING, T - RING):
            for x in range(RING, T - RING):
                if is_deco[y][x] and not touches_ring(stamps, x, y):
                    tp[x, y] = rng.choice(base_noise)
        for y in range(T):
            for x in range(T):
                if is_deco[y][x] and (x < RING or y < RING or x >= T - RING or y >= T - RING or touches_ring(stamps, x, y)):
                    occupied[y][x] = True
        inner = [s for s in stamps if not s["ring"]]
        count = max(1, round(len(inner) * density))
        for _ in range(count):
            place(tp, occupied, rng.choice(inner)["pixels"], rng)
        if flowers is not None:
            color, qty = flowers
            for _ in range(qty):
                place(tp, occupied, flower_stamp(color, rng), rng)
        out.paste(tile, (i * T, 0))
        print(f"{i}: {name}")
    out.save(OUT)
    print(f"salvo em {OUT.relative_to(ROOT)} ({len(VARIANTS)} variações, {len(stamps)} enfeites encontrados)")


def extract_stamps(px, is_deco) -> list[dict]:
    """Agrupa os pixels de enfeite em componentes conectados (8 vizinhos)."""
    seen = [[False] * T for _ in range(T)]
    stamps = []
    for y in range(T):
        for x in range(T):
            if not is_deco[y][x] or seen[y][x]:
                continue
            stack, comp = [(x, y)], []
            seen[y][x] = True
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < T and 0 <= ny < T and is_deco[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True
                            stack.append((nx, ny))
            minx = min(p[0] for p in comp)
            miny = min(p[1] for p in comp)
            ring = any(p[0] < RING + 1 or p[1] < RING + 1 or p[0] >= T - RING - 1 or p[1] >= T - RING - 1 for p in comp)
            stamps.append({
                "ring": ring,
                "cells": set(comp),
                "pixels": [(p[0] - minx, p[1] - miny, px[p[0], p[1]]) for p in comp],
            })
    return stamps


def touches_ring(stamps: list[dict], x: int, y: int) -> bool:
    for s in stamps:
        if (x, y) in s["cells"]:
            return s["ring"]
    return False


def place(tp, occupied, pixels, rng: random.Random, tries: int = 60) -> bool:
    w = max(p[0] for p in pixels) + 1
    h = max(p[1] for p in pixels) + 1
    lo = RING + 1
    for _ in range(tries):
        ox = rng.randint(lo, T - lo - w)
        oy = rng.randint(lo, T - lo - h)
        if any(occupied[oy + py + dy][ox + px_ + dx]
               for px_, py, _ in pixels for dy in (-1, 0, 1) for dx in (-1, 0, 1)
               if 0 <= oy + py + dy < T and 0 <= ox + px_ + dx < T):
            continue
        for px_, py, c in pixels:
            tp[ox + px_, oy + py] = c
            occupied[oy + py][ox + px_] = True
        return True
    return False


def flower_stamp(color: str, rng: random.Random) -> list[tuple]:
    """Florzinha de 3x3 em cruz com sombra embaixo; às vezes um par encostado."""
    petal, shade, center = FLOWER_COLORS[color]
    one = [(1, 0, petal), (0, 1, petal), (1, 1, center), (2, 1, shade), (1, 2, shade), (2, 2, FLOWER_SHADOW)]
    if rng.random() < 0.4:
        dx, dy = rng.choice([(3, 1), (2, 3), (-2, 2)])
        two = [(x + dx, y + dy, c) for x, y, c in one]
        allp = one + two
        minx = min(p[0] for p in allp)
        miny = min(p[1] for p in allp)
        merged: dict = {}
        for x, y, c in allp:
            key = (x - minx, y - miny)
            if key not in merged or c != FLOWER_SHADOW:
                merged[key] = c
        return [(k[0], k[1], c) for k, c in merged.items()]
    return one


if __name__ == "__main__":
    main()
