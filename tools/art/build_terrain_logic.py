"""Gera art/tiles/terrain_logic.png: um tile de cor por terreno da camada de lógica.

    python tools/art/build_terrain_logic.py

A coluna do tile é o `logic_id` do terreno (DualGridTerrain). Só aparece no editor,
com transparência, por cima do terreno desenhado. Novo terreno = nova cor no fim.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art/tiles/terrain_logic.png"
T = 32
# logic_id = posição na lista
COLORS = [
    ("terra", (107, 79, 52)),
    ("grama", (60, 170, 60)),
]


def main() -> None:
    img = Image.new("RGBA", (T * len(COLORS), T))
    draw = ImageDraw.Draw(img)
    for i, (_, rgb) in enumerate(COLORS):
        dark = tuple(int(c * 0.6) for c in rgb)
        draw.rectangle((i * T, 0, i * T + T - 1, T - 1), fill=rgb + (255,), outline=dark + (255,))
    img.save(OUT)
    print(f"salvo em {OUT.relative_to(ROOT)}: " + ", ".join(f"{i}={n}" for i, (n, _) in enumerate(COLORS)))


if __name__ == "__main__":
    main()
