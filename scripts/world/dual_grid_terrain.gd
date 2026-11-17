@tool
class_name DualGridTerrain
extends Resource
## Um terreno desenhado por dual grid (ver DualGridLayer): qual id da camada de lógica
## ele representa e de onde vêm os tiles visuais.

@export var display_name: String = ""
## Coordenada x do tile no atlas da camada de lógica (art/tiles/terrain_logic.png).
@export var logic_id: int = 0
## TileSet visual com o atlas 4x4 de cantos (layout em DualGrid.ATLAS_BY_MASK).
@export var tile_set: TileSet
@export var source_id: int = 0
## Variações do tile cheio: fonte, coordenadas e a chance de cada uma (0..1).
## A soma das chances é a fração de tiles cheios que vira variação (GAME_DESIGN §8: ~10–15%).
@export var variant_source_id: int = 1
@export var variant_coords: Array[Vector2i] = []
@export var variant_weights: PackedFloat32Array = PackedFloat32Array()
