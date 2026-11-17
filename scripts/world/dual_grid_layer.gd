@tool
class_name DualGridLayer
extends TileMapLayer
## Camada de lógica do terreno: pinte nela, no editor, com o TileSet de lógica
## (art/tiles/terrain_logic_tileset.tres: um tile de cor por terreno). Ela mesma fica
## invisível no jogo; para cada terreno de `terrains` ela mantém uma camada visual
## deslocada meio tile, com o tile escolhido pelos 4 cantos (dual grid, ver DualGrid).
##
## Os terrenos têm ordem: o de índice maior fica por cima e conta como preenchido nas
## camadas de baixo, então a borda de um chão por cima mostra o chão de baixo
## (GAME_DESIGN §7.1). Ids de lógica fora da lista não desenham nada.

## Terrenos em ordem de desenho (o primeiro fica embaixo).
@export var terrains: Array[DualGridTerrain] = []:
	set(value):
		terrains = value
		_rebuild_deferred()
## Opacidade da camada de lógica no editor (no jogo ela é sempre invisível).
@export_range(0.0, 1.0) var logic_opacity_in_editor: float = 0.25:
	set(value):
		logic_opacity_in_editor = value
		_apply_logic_visibility()
## Semente das variações do tile cheio.
@export var variant_seed: int = 0:
	set(value):
		variant_seed = value
		_rebuild_deferred()

var _displays: Array[TileMapLayer] = []
var _rebuild_queued: bool = false


func _ready() -> void:
	_apply_logic_visibility()
	_rebuild()


## Chamado pelo Godot quando células da lógica mudam (inclusive pintando no editor).
func _update_cells(coords: Array[Vector2i], forced_cleanup: bool) -> void:
	if forced_cleanup:
		for d: TileMapLayer in _displays:
			d.clear()
		return
	if _displays.size() != terrains.size():
		_rebuild_deferred()
		return
	var dirty: Dictionary = {}
	for cell: Vector2i in coords:
		for d: Vector2i in DualGrid.display_cells(cell):
			dirty[d] = true
	for d: Vector2i in dirty:
		_update_display_cell(d)


## Terreno (índice em `terrains`) da célula de lógica, ou -1.
func get_terrain_rank(cell: Vector2i) -> int:
	if get_cell_source_id(cell) == -1:
		return -1
	var id: int = get_cell_atlas_coords(cell).x
	for i: int in terrains.size():
		if terrains[i] != null and terrains[i].logic_id == id:
			return i
	return -1


func _rebuild_deferred() -> void:
	if _rebuild_queued or not is_inside_tree():
		return
	_rebuild_queued = true
	_rebuild.call_deferred()


func _rebuild() -> void:
	_rebuild_queued = false
	for d: TileMapLayer in _displays:
		d.queue_free()
	_displays.clear()
	var half: float = Units.TILE / 2.0
	for i: int in terrains.size():
		var layer: TileMapLayer = TileMapLayer.new()
		layer.name = "Display%d" % i
		layer.position = Vector2(-half, -half)
		layer.show_behind_parent = true
		layer.tile_set = terrains[i].tile_set if terrains[i] != null else null
		add_child(layer, false, Node.INTERNAL_MODE_FRONT)
		_displays.append(layer)
	var dirty: Dictionary = {}
	for cell: Vector2i in get_used_cells():
		for d: Vector2i in DualGrid.display_cells(cell):
			dirty[d] = true
	for d: Vector2i in dirty:
		_update_display_cell(d)


func _update_display_cell(display: Vector2i) -> void:
	var corners: Array[Vector2i] = DualGrid.corner_cells(display)
	var ranks: Array[int] = []
	for c: Vector2i in corners:
		ranks.append(get_terrain_rank(c))
	for i: int in _displays.size():
		var terrain: DualGridTerrain = terrains[i]
		var layer: TileMapLayer = _displays[i]
		if terrain == null or terrain.tile_set == null:
			continue
		var m: int = DualGrid.mask(ranks[0] >= i, ranks[1] >= i, ranks[2] >= i, ranks[3] >= i)
		if m == DualGrid.EMPTY_MASK:
			layer.erase_cell(display)
			continue
		# Variação do tile cheio só se não houver outro terreno inteiro por cima.
		if m == DualGrid.FULL_MASK and terrain.variant_coords.size() > 0:
			var v: int = DualGrid.pick_variant(display, terrain.variant_weights, variant_seed + i)
			if v >= 0 and v < terrain.variant_coords.size():
				layer.set_cell(display, terrain.variant_source_id, terrain.variant_coords[v])
				continue
		layer.set_cell(display, terrain.source_id, DualGrid.atlas_coords(m))


func _apply_logic_visibility() -> void:
	var alpha: float = logic_opacity_in_editor if Engine.is_editor_hint() else 0.0
	self_modulate = Color(1, 1, 1, alpha)
