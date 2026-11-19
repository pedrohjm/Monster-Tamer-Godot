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
    ("água", (44, 120, 200)),
    ("pedra", (150, 145, 130)),
    ("montanha", (204, 132, 64)),
    ("escada", (179, 143, 100)),
    ("areia", (247, 201, 120)),
    ("cachoeira", (43, 145, 154)),
]


def main() -> None:
    img = Image.new("RGBA", (T * len(COLORS), T))
    draw = ImageDraw.Draw(img)
    for i, (_, rgb) in enumerate(COLORS):
        dark = tuple(int(c * 0.6) for c in rgb)
        draw.rectangle((i * T, 0, i * T + T - 1, T - 1), fill=rgb + (255,), outline=dark + (255,))
        if COLORS[i][0] == "montanha":
            x = i * T
            draw.polygon([(x+3,24), (x+12,12), (x+15,16), (x+21,7), (x+29,24)],
                         fill=(85, 56, 39, 255))
            draw.polygon([(x+17,14), (x+21,7), (x+24,13), (x+21,12), (x+20,15)],
                         fill=(217, 226, 166, 255))
        elif COLORS[i][0] == "escada":
            x = i*T
            for j in range(4):
                draw.rectangle((x+5+3*j,22-5*j,x+16+3*j,24-5*j), fill=(88,57,39))
        elif COLORS[i][0] == "areia":
            x = i*T
            draw.line([(x+4,20),(x+10,17),(x+18,18),(x+27,13)],fill=(181,128,67),width=2)
            draw.line([(x+8,24),(x+15,22),(x+23,22)],fill=(255,234,178),width=2)
        elif COLORS[i][0] == "cachoeira":
            x = i*T
            draw.line([(x+5,8),(x+12,7),(x+23,8)],fill=(165,234,226),width=2)
            for dx, stop in [(9,23),(14,20),(20,23),(23,18)]:
                draw.line([(x+dx,9),(x+dx-1,stop)],fill=(209,250,244),width=2)
            draw.arc((x+4,18,x+28,26),0,180,fill=(159,229,218),width=2)
    img.save(OUT)
    print(f"salvo em {OUT.relative_to(ROOT)}: " + ", ".join(f"{i}={n}" for i, (n, _) in enumerate(COLORS)))


if __name__ == "__main__":
    main()
