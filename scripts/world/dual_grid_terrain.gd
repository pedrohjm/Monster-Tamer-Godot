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
## Number of 4x4 corner atlases in the repeating ground texture.
@export var atlas_repeat_size: Vector2i = Vector2i.ONE
## Variações do tile cheio: fonte, coordenadas e a chance de cada uma (0..1).
## A soma das chances é a fração de tiles cheios que vira variação (GAME_DESIGN §8: ~10–15%).
@export var variant_source_id: int = 1
@export var variant_coords: Array[Vector2i] = []
@export var variant_weights: PackedFloat32Array = PackedFloat32Array()
## Preenchimento sem bordas (ex.: água): com x >= 0, todo tile não vazio usa este tile,
## repetindo um bloco de `fill_size` tiles (padrões maiores que um tile).
@export var fill_coords: Vector2i = Vector2i(-1, -1)
@export var fill_size: Vector2i = Vector2i.ONE
## Fonte (no mesmo TileSet) do atlas 4x4 que aparece em volta deste terreno, embaixo
## dele (ex.: barranco e sombra da terra na água). -1 = nenhum.
@export var bank_source_id: int = -1
@export var bank_repeat_size: Vector2i = Vector2i.ONE
## Restringe a margem ao encontro com outro terreno (por exemplo, espuma só na água).
@export var bank_neighbor_logic_id: int = -1
## Material opcional da margem (por exemplo, a propria pedra frontal no contorno).
@export var bank_material: Material
## Fonte de tiles altos (`face_rows` células) desenhados abaixo das bordas sul, por baixo
## do terreno (ex.: paredão do planalto). Layout: o de DualGrid.ATLAS_BY_MASK com a linha
## multiplicada por `face_rows`, repetido `face_variants` vezes lado a lado (colunas + 4*v).
@export var face_source_id: int = -1
## Material opcional do paredao, incluindo a transicao entre a borda e os cantos.
@export var face_material: Material
@export var face_rows: int = 3
## Índice das versões do paredão recortadas pelo topo nas seis células que a projeção alcança.
@export var face_clip_lookup: PackedByteArray = PackedByteArray()
@export var face_variants: int = 1
## Desenha o paredão por cima do terreno (e da camada `overlay`) em vez de embaixo: para
## paredões que começam dentro da beirada do terreno e não podem ficar cobertos por ela.
@export var face_above: bool = false
## Usa a camada do paredão em toda máscara parcial (não só com borda sul): para levar
## junto a sombra projetada das bordas leste.
@export var face_all_masks: bool = false
## Ordena o paredão por Y junto com personagens e props (origem na base de cada tile,
## `y_sort_origin` no TileSet). O DualGridLayer precisa estar num pai com y_sort_enabled.
@export var face_y_sort: bool = false
## Fonte (no mesmo TileSet) do atlas 4x4 desenhado POR CIMA deste terreno, com a mesma
## máscara (ex.: borda de pedra do planalto cobrindo a beirada da grama). -1 = nenhum.
@export var overlay_source_id: int = -1
## Para água, o atlas sobreposto mostra o leito raso perto de células de terra.
@export var shallow_water_size: Vector2i = Vector2i.ZERO
## Cor multiplicada na camada visual do terreno (ex.: topo do planalto mais claro).
@export var tint: Color = Color.WHITE
