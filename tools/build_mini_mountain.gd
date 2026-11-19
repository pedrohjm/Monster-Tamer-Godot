extends SceneTree
## Rebuilds the editable TileSet and two-tier mountain from the original sprites.
## python tools/art/build_mini_mountain_atlas.py [source_a.png source_b.png]
## Godot --headless --path . --import
## Godot --headless --path . -s res://tools/build_mini_mountain.gd

const TILE: int = 32
const TILESET_PATH: String = "res://art/tiles/mini_mountain_tileset.tres"
const SCENE_PATH: String = "res://scenes/world/mini_mountain.tscn"


const PEERS: Array[TileSet.CellNeighbor] = [
	TileSet.CELL_NEIGHBOR_TOP_SIDE, TileSet.CELL_NEIGHBOR_TOP_RIGHT_CORNER,
	TileSet.CELL_NEIGHBOR_RIGHT_SIDE, TileSet.CELL_NEIGHBOR_BOTTOM_RIGHT_CORNER,
	TileSet.CELL_NEIGHBOR_BOTTOM_SIDE, TileSet.CELL_NEIGHBOR_BOTTOM_LEFT_CORNER,
	TileSet.CELL_NEIGHBOR_LEFT_SIDE, TileSet.CELL_NEIGHBOR_TOP_LEFT_CORNER,
]


func _initialize() -> void:
	var kit: TileSet = TileSet.new()
	kit.tile_size = Vector2i(TILE, TILE)
	_add_terrain(kit)
	_add_atlas(kit, "res://art/tiles/mini_mountain_details.png", "Escadas e pedras", 3)
	_add_atlas(kit, "res://art/tiles/mini_mountain_source_a.png", "Original A", 1)
	_add_atlas(kit, "res://art/tiles/mini_mountain_source_b.png", "Original B", 2)
	var err: Error = ResourceSaver.save(kit, TILESET_PATH)
	if err != OK:
		quit(err)
		return
	# Reload so the packed scene references the external, reusable .tres.
	kit = load(TILESET_PATH) as TileSet
	var region: Region = Region.new()
	region.name = "MiniMountain"
	region.bounds = Rect2i(16, 16, 640, 512)
	region.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	# The region stays an atomic group in World's y-sort; tiers use explicit
	# draw order within it, so the upper wall never falls behind the lower top.
	region.y_sort_enabled = false
	region.set_meta("description", "Mini montanha de dois andares; tiles de 32x32 dos dois PNGs originais")
	var ground: DualGridLayer = DualGridLayer.new()
	ground.name = "Terrain"
	ground.tile_set = load("res://art/tiles/terrain_logic_tileset.tres")
	ground.terrains = [load("res://art/tiles/sand_terrain.tres") as DualGridTerrain,
		load("res://art/tiles/grass_terrain.tres") as DualGridTerrain]
	ground.z_index = -2
	ground.self_modulate = Color(1, 1, 1, 0.25)
	for y: int in 17:
		for x: int in 21:
			ground.set_cell(Vector2i(x, y), 0, Vector2i(1, 0))
	_add(region, ground)

	var lower: TileMapLayer = _layer(region, "Andar1", kit, 0)
	_paint_rows(lower, 1, [
		Vector2i(6, 14), Vector2i(4, 15), Vector2i(3, 16), Vector2i(3, 16),
		Vector2i(3, 16), Vector2i(4, 16), Vector2i(5, 14),
	])
	_stairs(_layer(region, "EscadaAndar1", kit, 1), Vector2i(11, 7), 0)
	var upper: TileMapLayer = _layer(region, "Andar2", kit, 2)
	_paint_rows(upper, 2, [Vector2i(7, 11), Vector2i(6, 12), Vector2i(6, 12)])
	_stairs(_layer(region, "EscadaAndar2", kit, 3), Vector2i(8, 4), 3)
	var rocks: TileMapLayer = _layer(region, "Pedras", kit, 4)
	for cell: Vector2i in [Vector2i(11, 3), Vector2i(5, 5), Vector2i(14, 10)]:
		rocks.set_cell(cell, 3, Vector2i(6, 0))

	var entities: Node2D = Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	_add(region, entities)
	var spawn: Marker2D = Marker2D.new()
	spawn.name = "Spawn"
	spawn.position = Vector2(320, 208)
	_add(region, spawn)
	var packed: PackedScene = PackedScene.new()
	err = packed.pack(region)
	if err == OK:
		err = ResourceSaver.save(packed, SCENE_PATH)
	region.free()
	print("Mini montanha salva: %s (erro=%d)" % [SCENE_PATH, err])
	quit(err)


func _add_terrain(kit: TileSet) -> void:
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(
		"res://art/tiles/mini_mountain_atlas.json"))
	var masks: Array = layout["masks"]
	kit.add_terrain_set()
	kit.set_terrain_set_mode(0, TileSet.TERRAIN_MODE_MATCH_CORNERS_AND_SIDES)
	kit.add_terrain(0)
	kit.set_terrain_name(0, 0, "Montanha")
	kit.set_terrain_color(0, 0, Color("#86b94a"))
	var atlas := TileSetAtlasSource.new()
	atlas.resource_name = "Montanha"
	atlas.texture_region_size = Vector2i(TILE, 3 * TILE)
	atlas.texture = load("res://art/tiles/mini_mountain_atlas.png")
	kit.add_source(atlas, 0)
	var rows: int = ceili(masks.size() / 16.0)
	for variant: int in int(layout["variants"]):
		for i: int in masks.size():
			var at := Vector2i(i % 16, i / 16 + rows * variant)
			atlas.create_tile(at)
			var data: TileData = atlas.get_tile_data(at, 0)
			data.texture_origin = Vector2i(0, -TILE)
			data.terrain_set = 0
			data.terrain = 0
			for bit: int in PEERS.size():
				if int(masks[i]) & (1 << bit):
					data.set_terrain_peering_bit(PEERS[bit], 0)


func _paint_rows(layer: TileMapLayer, first_row: int, spans: Array[Vector2i]) -> void:
	var cells: Array[Vector2i] = []
	for y: int in spans.size():
		for x: int in range(spans[y].x, spans[y].y + 1):
			cells.append(Vector2i(x, y + first_row))
	layer.y_sort_enabled = true
	layer.set_cells_terrain_connect(cells, 0, 0, false)


func _stairs(layer: TileMapLayer, at: Vector2i, atlas_x: int) -> void:
	var details: TileSetAtlasSource = layer.tile_set.get_source(3)
	for y: int in 3:
		for x: int in 3:
			var coord := Vector2i(atlas_x + x, y)
			if details.has_tile(coord):
				layer.set_cell(at + Vector2i(x, y), 3, coord)


func _add_atlas(kit: TileSet, path: String, label: String, id: int) -> void:
	var atlas: TileSetAtlasSource = TileSetAtlasSource.new()
	atlas.resource_name = label
	atlas.texture = load(path) as Texture2D
	atlas.texture_region_size = Vector2i(TILE, TILE)
	var img: Image = atlas.texture.get_image()
	for y: int in img.get_height() / TILE:
		for x: int in img.get_width() / TILE:
			if not img.get_region(Rect2i(x * TILE, y * TILE, TILE, TILE)).is_invisible():
				atlas.create_tile(Vector2i(x, y))
	kit.add_source(atlas, id)


func _layer(region: Node2D, label: String, kit: TileSet, draw_order: int) -> TileMapLayer:
	var layer: TileMapLayer = TileMapLayer.new()
	layer.name = label
	layer.tile_set = kit
	layer.z_index = draw_order
	_add(region, layer)
	return layer


func _add(region: Node2D, child: Node) -> void:
	region.add_child(child)
	child.owner = region
