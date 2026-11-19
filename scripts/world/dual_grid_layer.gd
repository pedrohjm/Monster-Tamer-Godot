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
## z_index das camadas de chão (terreno, margem, borda por cima). Com o paredão ordenado
## por Y (DualGridTerrain.face_y_sort), deixe o chão abaixo das entidades (ex.: -1).
@export var floor_z_index: int = 0:
	set(value):
		floor_z_index = value
		_rebuild_deferred()
## Semente das variações do tile cheio.
@export var variant_seed: int = 0:
	set(value):
		variant_seed = value
		_rebuild_deferred()

## Quinto pincel da paleta (id 4): montanha no formato dual grid. Ela entra sozinha por
## cima dos terrenos de qualquer camada, sem precisar estar em `terrains`; nas camadas de
## chão a grama fica por baixo dela.
const MOUNTAIN_ID := 4
const STAIRS_ID := 5
const STAIRS_SOURCE := 5
const SAND_ID := 6
const WATERFALL_ID := 7
const WATERFALL_SOURCE := 6
const DIRT_ID := 0
const MOUNTAIN_TERRAIN := "res://art/tiles/mountain_terrain.tres"
const GRASS_TERRAIN := "res://art/tiles/grass_terrain.tres"
## Terrenos em uso: `terrains` mais a montanha, quando entra.
var _all: Array[DualGridTerrain] = []
## A montanha preenche os terrenos de baixo só nas camadas de chão (com a grama).
var _mountain_fills_below: bool = false
var _displays: Array[TileMapLayer] = []
## Camada de margem de cada terreno (null se ele não tiver `bank_source_id`).
var _banks: Array[TileMapLayer] = []
## Camada de paredão de cada terreno (null se ele não tiver `face_source_id`).
var _faces: Array[TileMapLayer] = []
## Camada por cima de cada terreno (null se ele não tiver `overlay_source_id`).
var _overlays: Array[TileMapLayer] = []
var _rebuild_queued: bool = false
var _has_shallows: bool = false
var _sand_rank := -1
var _cliff_details: TileMapLayer


func _ready() -> void:
	_apply_logic_visibility()
	_rebuild()


## Chamado pelo Godot quando células da lógica mudam (inclusive pintando no editor).
func _update_cells(coords: Array[Vector2i], forced_cleanup: bool) -> void:
	if forced_cleanup:
		if is_instance_valid(_cliff_details):
			_cliff_details.clear()
		for d: TileMapLayer in _displays:
			d.clear()
		for b: TileMapLayer in _banks + _faces + _overlays:
			if b != null:
				b.clear()
		return
	if _displays.size() != _all.size():
		_rebuild_deferred()
		return
	var dirty: Dictionary = {}
	for cell: Vector2i in coords:
		if _has_shallows:
			# A profundidade também depende dos vizinhos dos quatro cantos.
			for dy in range(-1, 3):
				for dx in range(-1, 3):
					dirty[cell + Vector2i(dx, dy)] = true
		else:
			for d: Vector2i in DualGrid.display_cells(cell):
				dirty[d] = true
	# Uma mudança no topo também pode descobrir o paredão da fileira de trás.
	for i in _faces.size():
		if _faces[i] == null or _all[i].face_clip_lookup.is_empty():
			continue
		for cell in coords:
			for dy in range(-2, 2):
				for dx in range(-1, 2):
					var d := cell + Vector2i(dx, dy)
					if _faces[i].get_cell_source_id(d) >= 0:
						dirty[d] = true
	for d: Vector2i in dirty:
		_update_display_cell(d)
	var detail_cells: Dictionary[Vector2i, bool] = {}
	for cell in coords:
		for dy in [-1, 0]:
			for dx in [-1, 0, 1]:
				detail_cells[cell + Vector2i(dx, dy)] = true
	for cell in detail_cells:
		_update_cliff_detail(cell)


## Terreno (índice na lista em uso) da célula de lógica, ou -1.
func get_terrain_rank(cell: Vector2i) -> int:
	if get_cell_source_id(cell) == -1:
		return -1
	var id: int = get_cell_atlas_coords(cell).x
	if id == STAIRS_ID or id == WATERFALL_ID:
		id = MOUNTAIN_ID
	for i: int in _all.size():
		if _all[i] != null and _all[i].logic_id == id:
			return i
	return -1


## Lista em uso: `terrains` e a montanha por cima de tudo (pincel 5 em qualquer camada).
func _terrains_in_use() -> Array[DualGridTerrain]:
	var list: Array[DualGridTerrain] = terrains.duplicate()
	_mountain_fills_below = false
	for t: DualGridTerrain in list:
		if t != null and t.logic_id == MOUNTAIN_ID:
			_mountain_fills_below = true
			return list
		if t != null and t.resource_path == GRASS_TERRAIN:
			_mountain_fills_below = true
	if ResourceLoader.exists(MOUNTAIN_TERRAIN):
		list.append(load(MOUNTAIN_TERRAIN) as DualGridTerrain)
	return list


## Se a célula (com o terreno `rank`) conta como cheia para o terreno `i`. O terreno de
## cima conta como cheio nos de baixo (a borda dele mostra o chão de baixo), menos a
## montanha numa camada de planalto: ali o chão vem da camada Terrain de baixo, e o
## planalto não deve aparecer embaixo dela.
func _fills(rank: int, i: int) -> bool:
	if rank < i:
		return false
	if rank != i and not _mountain_fills_below and _all[rank] != null and _all[rank].logic_id == MOUNTAIN_ID:
		return false
	return true


func _rebuild_deferred() -> void:
	if _rebuild_queued or not is_inside_tree():
		return
	_rebuild_queued = true
	_rebuild.call_deferred()


func _rebuild() -> void:
	_rebuild_queued = false
	_all = _terrains_in_use()
	_has_shallows = false
	_sand_rank = -1
	if is_instance_valid(_cliff_details):
		_cliff_details.queue_free()
	_cliff_details = null
	# Paredão ordenado por Y (ex.: a montanha na camada de chão) só entra na ordenação dos
	# personagens se esta camada também ordenar por Y.
	for t: DualGridTerrain in _all:
		if t != null and t.shallow_water_size != Vector2i.ZERO:
			_has_shallows = true
		if t != null and t.face_source_id >= 0 and t.face_y_sort and not y_sort_enabled:
			y_sort_enabled = true
	for d: TileMapLayer in _displays:
		d.queue_free()
	for b: TileMapLayer in _banks + _faces + _overlays:
		if b != null:
			b.queue_free()
	_displays.clear()
	_banks.clear()
	_faces.clear()
	_overlays.clear()
	for i: int in _all.size():
		var terrain: DualGridTerrain = _all[i]
		if terrain != null and terrain.logic_id == SAND_ID:
			_sand_rank = i
		var tile_set_i: TileSet = terrain.tile_set if terrain != null else null
		# Paredão e margem ficam embaixo do terreno (e por cima dos terrenos de baixo).
		var face: TileMapLayer = null
		var has_face: bool = terrain != null and terrain.face_source_id >= 0
		if has_face and not terrain.face_above:
			face = _new_display("Face%d" % i, tile_set_i, terrain.face_y_sort)
			face.material = terrain.face_material
		var bank: TileMapLayer = null
		if terrain != null and terrain.bank_source_id >= 0:
			bank = _new_display("Bank%d" % i, tile_set_i)
			bank.material = terrain.bank_material
		_banks.append(bank)
		var display_layer: TileMapLayer = _new_display("Display%d" % i, tile_set_i)
		if terrain != null:
			display_layer.modulate = terrain.tint
		_displays.append(display_layer)
		var overlay: TileMapLayer = null
		if terrain != null and terrain.overlay_source_id >= 0:
			overlay = _new_display("Overlay%d" % i, tile_set_i)
		_overlays.append(overlay)
		if has_face and terrain.face_above:
			face = _new_display("Face%d" % i, tile_set_i, terrain.face_y_sort)
			face.material = terrain.face_material
		_faces.append(face)
		if terrain != null and terrain.logic_id == MOUNTAIN_ID and tile_set_i != null:
			_cliff_details = _new_display("DetalhesDoParedao", tile_set_i, true)
			_cliff_details.position = Vector2.ZERO
	var dirty: Dictionary = {}
	for cell: Vector2i in get_used_cells():
		_update_cliff_detail(cell)
		for d: Vector2i in DualGrid.display_cells(cell):
			dirty[d] = true
	for d: Vector2i in dirty:
		_update_display_cell(d)


func _new_display(layer_name: String, tile_set_value: TileSet, y_sorted: bool = false) -> TileMapLayer:
	var half: float = Units.TILE / 2.0
	var layer: TileMapLayer = TileMapLayer.new()
	layer.name = layer_name
	layer.position = Vector2(-half, -half)
	layer.tile_set = tile_set_value
	if y_sorted:
		# Cada tile entra na ordenação por Y do pai, pela origem na base, no mesmo z das
		# entidades (a camada de chão pode ter z negativo, ex.: a montanha na Terrain).
		layer.y_sort_enabled = true
		layer.z_as_relative = false
		layer.z_index = 0
	else:
		layer.show_behind_parent = true
		layer.z_index = floor_z_index
	add_child(layer, false, Node.INTERNAL_MODE_FRONT)
	return layer


func _update_display_cell(display: Vector2i) -> void:
	var corners: Array[Vector2i] = DualGrid.corner_cells(display)
	var ranks: Array[int] = []
	for c: Vector2i in corners:
		ranks.append(get_terrain_rank(c))
	var has_sand := _sand_rank >= 0 and _sand_rank in ranks
	var sand_at_water := has_sand and _bank_neighbor_present(_all[_sand_rank].bank_neighbor_logic_id, ranks)
	for i: int in _displays.size():
		var terrain: DualGridTerrain = _all[i]
		var layer: TileMapLayer = _displays[i]
		var bank: TileMapLayer = _banks[i]
		if terrain == null or terrain.tile_set == null:
			continue
		var m: int = DualGrid.mask(_fills(ranks[0], i), _fills(ranks[1], i), _fills(ranks[2], i), _fills(ranks[3], i))
		# Na água a praia acompanha só seus próprios cantos, inclusive onde termina no barranco.
		if i == _sand_rank and sand_at_water:
			m = DualGrid.mask(ranks[0] == i, ranks[1] == i, ranks[2] == i, ranks[3] == i)
		elif (i == _sand_rank and not has_sand) or (terrain.logic_id == DIRT_ID and has_sand and not sand_at_water and i not in ranks):
			m = DualGrid.EMPTY_MASK
		var face: TileMapLayer = _faces[i]
		if face != null:
			var wants_face: bool = DualGrid.has_south_edge(m)
			if terrain.face_all_masks:
				wants_face = m != DualGrid.EMPTY_MASK and m != DualGrid.FULL_MASK
			if wants_face:
				face.set_cell(display, terrain.face_source_id, _face_coords(terrain, display, m, i))
			else:
				face.erase_cell(display)
		if bank != null:
			if m == DualGrid.EMPTY_MASK or m == DualGrid.FULL_MASK or _side_under_wall(display, i, m) or not _bank_neighbor_present(terrain.bank_neighbor_logic_id, ranks):
				bank.erase_cell(display)
			else:
				var bank_coords := DualGrid.atlas_coords(m) + 4 * DualGrid.fill_tile(display, Vector2i.ZERO, terrain.bank_repeat_size)
				bank.set_cell(display, terrain.bank_source_id, bank_coords)
		var overlay: TileMapLayer = _overlays[i]
		if overlay != null:
			if terrain.shallow_water_size != Vector2i.ZERO:
				_update_shallows(overlay, display, terrain, i, m, corners, ranks)
			elif m == DualGrid.EMPTY_MASK or m == DualGrid.FULL_MASK:
				overlay.erase_cell(display)
			else:
				overlay.set_cell(display, terrain.overlay_source_id, DualGrid.atlas_coords(m))
		if m == DualGrid.EMPTY_MASK:
			layer.erase_cell(display)
			continue
		if terrain.fill_coords.x >= 0:
			# Preenchimento sem bordas: só onde os 4 cantos têm o terreno (ou um de cima).
			# Tile parcial aqui é a borda da área pintada; preencher vazaria meio tile.
			if m == DualGrid.FULL_MASK:
				layer.set_cell(display, terrain.source_id, DualGrid.fill_tile(display, terrain.fill_coords, terrain.fill_size))
			else:
				layer.erase_cell(display)
			continue
		# Variação do tile cheio só se não houver outro terreno inteiro por cima.
		if m == DualGrid.FULL_MASK and terrain.variant_coords.size() > 0:
			var original_rank := i - int(_sand_rank >= 0 and i > _sand_rank)
			var v: int = DualGrid.pick_variant(display, terrain.variant_weights, variant_seed + original_rank)
			if v >= 0 and v < terrain.variant_coords.size():
				layer.set_cell(display, terrain.variant_source_id, terrain.variant_coords[v])
				continue
		var coords := DualGrid.atlas_coords(m)
		if terrain.atlas_repeat_size != Vector2i.ONE:
			coords += 4 * DualGrid.fill_tile(display, Vector2i.ZERO, terrain.atlas_repeat_size)
		layer.set_cell(display, terrain.source_id, coords)


func _exposed_front(cell: Vector2i) -> bool:
	return get_cell_atlas_coords(cell + Vector2i.DOWN).x not in [MOUNTAIN_ID, STAIRS_ID, WATERFALL_ID]


func _waterfall_at(cell: Vector2i) -> bool:
	return get_cell_atlas_coords(cell).x == WATERFALL_ID and _exposed_front(cell)


func _update_cliff_detail(cell: Vector2i) -> void:
	if _cliff_details == null:
		return
	var tile := get_cell_atlas_coords(cell).x
	if tile == STAIRS_ID and _exposed_front(cell):
		_cliff_details.set_cell(cell, STAIRS_SOURCE, Vector2i.ZERO)
	elif tile == WATERFALL_ID and _exposed_front(cell):
		var left := _waterfall_at(cell + Vector2i.LEFT)
		var right := _waterfall_at(cell + Vector2i.RIGHT)
		var row := 0
		if left and right:
			row = 2
		elif right:
			row = 1
		elif left:
			row = 3
		_cliff_details.set_cell(cell, WATERFALL_SOURCE, Vector2i(0, row))
	else:
		_cliff_details.erase_cell(cell)


func _bank_neighbor_present(logic_id: int, ranks: Array[int]) -> bool:
	if logic_id < 0:
		return true
	# O preenchimento da água termina antes das células vazias na borda do mapa.
	if -1 in ranks:
		return false
	for rank in ranks:
		if _all[rank].logic_id == logic_id:
			return true
	return false


func _update_shallows(overlay: TileMapLayer, display: Vector2i, terrain: DualGridTerrain,
		water_rank: int, mask: int, corners: Array[Vector2i], ranks: Array[int]) -> void:
	var shore_mask := 0
	if mask == DualGrid.FULL_MASK and water_rank in ranks:
		for k in 4:
			if ranks[k] > water_rank or _water_near_land(corners[k], water_rank):
				shore_mask |= 8 >> k
	if shore_mask == 0:
		overlay.erase_cell(display)
		return
	var phase := DualGrid.fill_tile(display, Vector2i.ZERO, terrain.shallow_water_size)
	overlay.set_cell(display, terrain.overlay_source_id, DualGrid.atlas_coords(shore_mask) + 4 * phase)


func _water_near_land(cell: Vector2i, water_rank: int) -> bool:
	for offset: Vector2i in [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]:
		if get_terrain_rank(cell + offset) > water_rank:
			return true
	return false


func _face_coords(terrain: DualGridTerrain, display: Vector2i, mask: int, rank: int) -> Vector2i:
	if not terrain.face_clip_lookup.is_empty():
		var bits := 0
		for y in 4:
			for x in 3:
				var cell := display + Vector2i(x - 1, y - 1)
				if _fills(get_terrain_rank(cell), rank):
					bits |= 1 << (y * 3 + x)
		var group := int(terrain.face_clip_lookup[bits]) - 1
		if group >= 0:
			var variant := posmod(display.x, terrain.face_variants)
			return Vector2i((group % 4) * 4 + variant, (4 + group / 4) * terrain.face_rows)
	return DualGrid.face_coords(mask, display, terrain.face_rows, terrain.face_variants)


## Degrau na borda (dual grid): a lateral de um degrau fica embaixo do paredão da parte
## de cima quando o lado vazio desta peça tem, logo acima, uma célula do terreno (a borda
## sul dela solta o paredão por cima desse vazio). Ali a margem (faixa da lateral) não
## entra: ela ficaria solta entre o paredão de cima e o degrau seguinte.
func _side_under_wall(display: Vector2i, i: int, m: int) -> bool:
	if _all[i] == null or _all[i].face_source_id < 0:
		return false
	var tl: bool = m & DualGrid.TL != 0
	var tr: bool = m & DualGrid.TR != 0
	var bl: bool = m & DualGrid.BL != 0
	var br: bool = m & DualGrid.BR != 0
	# Cantos da peça visual: TL=(x-1,y-1) TR=(x,y-1) BL=(x-1,y) BR=(x,y).
	if tl and not tr and not br:
		return _fills(get_terrain_rank(display + Vector2i(0, -2)), i)      # lado leste vazio
	if tr and not tl and not bl:
		return _fills(get_terrain_rank(display + Vector2i(-1, -2)), i)     # lado oeste vazio
	return false


func _apply_logic_visibility() -> void:
	var alpha: float = logic_opacity_in_editor if Engine.is_editor_hint() else 0.0
	# Só muda se for diferente: com o valor já salvo na cena, abrir no editor não a
	# marca como alterada (*).
	if not is_equal_approx(self_modulate.a, alpha):
		self_modulate = Color(1, 1, 1, alpha)
