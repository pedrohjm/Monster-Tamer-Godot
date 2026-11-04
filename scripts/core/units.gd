class_name Units
extends RefCounted
## Conversão entre tiles (unidade de design) e pixels (unidade do Godot 2D).
## Use sempre estas funções em vez de escrever 32 no código (GAME_DESIGN §8).

const TILE: int = 32


static func tiles(count: float) -> float:
	return count * TILE


static func to_tiles(pixels: float) -> float:
	return pixels / TILE
