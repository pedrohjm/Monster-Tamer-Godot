class_name DualGrid
extends RefCounted
## Matemática pura do "dual grid": a camada de lógica guarda um terreno por célula e
## a camada visual fica deslocada meio tile, com cada tile visual apoiado nos centros
## de 4 células de lógica. O tile visual é escolhido pelos 4 cantos (16 combinações),
## no layout de atlas 4x4 usado pelos tilesets do projeto (art/tiles/grass.png).

## Bits dos cantos na máscara.
const TL: int = 8
const TR: int = 4
const BL: int = 2
const BR: int = 1

## Máscara de cantos (TL TR BL BR) -> coordenada no atlas 4x4.
const ATLAS_BY_MASK: Array[Vector2i] = [
	Vector2i(0, 3),  # 0000 vazio
	Vector2i(1, 3),  # 0001 BR
	Vector2i(0, 0),  # 0010 BL
	Vector2i(3, 0),  # 0011 BL BR
	Vector2i(0, 2),  # 0100 TR
	Vector2i(1, 0),  # 0101 TR BR
	Vector2i(2, 3),  # 0110 TR BL
	Vector2i(1, 1),  # 0111 TR BL BR
	Vector2i(3, 3),  # 1000 TL
	Vector2i(0, 1),  # 1001 TL BR
	Vector2i(3, 2),  # 1010 TL BL
	Vector2i(2, 0),  # 1011 TL BL BR
	Vector2i(1, 2),  # 1100 TL TR
	Vector2i(2, 2),  # 1101 TL TR BR
	Vector2i(3, 1),  # 1110 TL TR BL
	Vector2i(2, 1),  # 1111 cheio
]
const EMPTY_MASK: int = 0
const FULL_MASK: int = 15


## Máscara a partir dos 4 cantos preenchidos.
static func mask(tl: bool, tr: bool, bl: bool, br: bool) -> int:
	return (TL if tl else 0) | (TR if tr else 0) | (BL if bl else 0) | (BR if br else 0)


static func atlas_coords(corner_mask: int) -> Vector2i:
	return ATLAS_BY_MASK[corner_mask]


## Células de lógica que formam os cantos do tile visual `display` (TL, TR, BL, BR).
## O tile visual (x, y) fica entre as células (x-1, y-1) e (x, y).
static func corner_cells(display: Vector2i) -> Array[Vector2i]:
	return [display + Vector2i(-1, -1), display + Vector2i(0, -1), display + Vector2i(-1, 0), display]


## Tiles visuais que usam a célula de lógica `cell` como canto.
static func display_cells(cell: Vector2i) -> Array[Vector2i]:
	return [cell, cell + Vector2i(1, 0), cell + Vector2i(0, 1), cell + Vector2i(1, 1)]


## Escolhe uma variação para o tile cheio de forma estável pela posição (o mapa não
## muda ao reabrir). Devolve -1 para o tile base ou o índice em `weights`, onde cada
## peso é a chance (0..1) daquela variação; a soma deve ficar abaixo de 1.
static func pick_variant(cell: Vector2i, weights: PackedFloat32Array, seed_value: int = 0) -> int:
	var roll: float = hash01(cell, seed_value)
	var acc: float = 0.0
	for i: int in weights.size():
		acc += weights[i]
		if roll < acc:
			return i
	return -1


## Número pseudoaleatório em [0, 1) determinado pela célula e pela semente.
static func hash01(cell: Vector2i, seed_value: int = 0) -> float:
	var h: int = (cell.x * 73856093) ^ (cell.y * 19349663) ^ (seed_value * 83492791)
	h = (h ^ (h >> 13)) * 1274126177
	h = h ^ (h >> 16)
	return float(h & 0xFFFFFF) / float(0x1000000)
