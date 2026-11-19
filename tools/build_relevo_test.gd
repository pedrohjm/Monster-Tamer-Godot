extends SceneTree
## Monta o kit original de art/examples/Relevo, sem redesenhar suas texturas.
## Godot --headless --path . -s res://tools/build_relevo_test.gd
## A cena fica ao lado dos estilos A/B/C na main e pode ser editada no TileMap.

const T: int = 32
const OUT: String = "res://scenes/world/relevo_test.tscn"
const SHAPE: Array[String] = [".####.", "######", "######", "##..##"]
# O kit usa N/E/S/O nos quatro bits baixos e NE/SE/SO/NO nos altos.
const NEIGHBORS: Array[Vector2i] = [
	Vector2i(0, -1), Vector2i(1, 0), Vector2i(0, 1), Vector2i(-1, 0),
	Vector2i(1, -1), Vector2i(1, 1), Vector2i(-1, 1), Vector2i(-1, -1),
]


func _initialize() -> void:
	var kit: TileSet = load("res://art/examples/Relevo/Relevo.tres") as TileSet
	var index: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(
		"res://art/examples/Relevo/indice.json"))
	var rows: Dictionary = {}
	for entry: Dictionary in index["CliffTop"]:
		var parts: PackedStringArray = String(entry["name"]).split("_")
		rows[int(parts[1].trim_prefix("M"))] = int(entry["atlas"][1])

	var region: Region = Region.new()
	region.name = "RelevoTest"
	region.bounds = Rect2i(16, 16, 352, 288)
	region.y_sort_enabled = true
	var ground: DualGridLayer = DualGridLayer.new()
	ground.name = "Terrain"
	ground.tile_set = load("res://art/tiles/terrain_logic_tileset.tres")
	ground.terrains = [load("res://art/tiles/sand_terrain.tres") as DualGridTerrain,
		load("res://art/tiles/grass_terrain.tres") as DualGridTerrain]
	ground.z_index = -2
	ground.self_modulate = Color(1, 1, 1, 0.25)
	for y: int in 10:
		for x: int in 12:
			ground.set_cell(Vector2i(x, y), 0, Vector2i(1, 0))
	_add(region, ground)

	# Paredes projetadas 64 px para leste e 96 px para sul. Os offsets originais
	# do TileSet mantem o inicio de cada parede alinhado ao tile de topo.
	var front: TileMapLayer = _layer(region, "ParedeFrontal", kit, true)
	var side: TileMapLayer = _layer(region, "ParedeLateral", kit, true)
	var top: TileMapLayer = _layer(region, "Topo", kit, false)
	top.z_index = 1
	for y: int in SHAPE.size():
		for x: int in SHAPE[y].length():
			var cell: Vector2i = Vector2i(x, y)
			if not _filled(cell):
				continue
			var mask: int = _mask(cell)
			var row: int = rows[mask]
			var at: Vector2i = cell + Vector2i(1, 1)
			top.set_cell(at, 0, Vector2i((x + y * 7) % 32, row))
			if not _filled(cell + Vector2i.DOWN):
				front.set_cell(at, 1, Vector2i((x + y * 3) % 8, row))
			if not _filled(cell + Vector2i.RIGHT):
				side.set_cell(at, 2, Vector2i((x + y) % 4, row))

	var entities: Node2D = Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	_add(region, entities)
	var spawn: Marker2D = Marker2D.new()
	spawn.name = "Spawn"
	spawn.position = Vector2(112, 144)
	_add(region, spawn)
	var packed: PackedScene = PackedScene.new()
	packed.pack(region)
	var err: Error = ResourceSaver.save(packed, OUT)
	region.free()
	print("salvo %s, erro=%d" % [OUT, err])
	quit(err)


func _add(region: Node2D, child: Node) -> void:
	region.add_child(child)
	child.owner = region


func _layer(region: Node2D, layer_name: String, kit: TileSet, sorted: bool) -> TileMapLayer:
	var layer: TileMapLayer = TileMapLayer.new()
	layer.name = layer_name
	layer.tile_set = kit
	layer.y_sort_enabled = sorted
	_add(region, layer)
	return layer


func _filled(cell: Vector2i) -> bool:
	return cell.y >= 0 and cell.y < SHAPE.size() \
		and cell.x >= 0 and cell.x < SHAPE[cell.y].length() and SHAPE[cell.y][cell.x] == "#"


func _mask(cell: Vector2i) -> int:
	var mask: int = 0
	for i: int in NEIGHBORS.size():
		if _filled(cell + NEIGHBORS[i]):
			mask |= 1 << i
	# Diagonais so contam quando os dois lados do canto existem (47 mascaras).
	for i: int in 4:
		var sides: int = (1 << i) | (1 << ((i + 1) % 4))
		if mask & sides != sides:
			mask &= ~(1 << (i + 4))
	return mask
