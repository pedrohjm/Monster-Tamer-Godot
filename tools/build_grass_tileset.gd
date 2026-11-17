extends SceneTree
## Gera os recursos do terreno de grama por dual grid e a cena de teste:
##   art/tiles/grass_tileset.tres          atlas 4x4 de cantos + variações do tile cheio
##   art/tiles/terrain_logic_tileset.tres  um tile de cor por terreno (pintar no editor)
##   art/tiles/grass_terrain.tres          DualGridTerrain da grama
##   scenes/world/region_grass_test.tscn   região de teste com um DualGridLayer
##
##   python tools/art/build_terrain_logic.py
##   python tools/art/build_grass_variants.py
##   Godot --headless --path . --import
##   Godot --headless --path . -s res://tools/build_grass_tileset.gd

const T: int = 32
const GRASS_PNG: String = "res://art/tiles/grass.png"
const VARIANTS_PNG: String = "res://art/tiles/grass_variants.png"
const LOGIC_PNG: String = "res://art/tiles/terrain_logic.png"
const GRASS_TILESET_OUT: String = "res://art/tiles/grass_tileset.tres"
const LOGIC_TILESET_OUT: String = "res://art/tiles/terrain_logic_tileset.tres"
const GRASS_TERRAIN_OUT: String = "res://art/tiles/grass_terrain.tres"
const SCENE_OUT: String = "res://scenes/world/region_grass_test.tscn"
const REGION_SCRIPT: String = "res://scripts/world/region.gd"

## Ids da camada de lógica (coluna em terrain_logic.png).
const LOGIC_GROUND: int = 0
const LOGIC_GRASS: int = 1
const LOGIC_COUNT: int = 2

## Chance de cada variação do tile cheio, na ordem das colunas de grass_variants.png
## (ver tools/art/build_grass_variants.py): 3 misturas e 3 com flores.
const VARIANT_WEIGHTS: Array[float] = [0.06, 0.06, 0.05, 0.02, 0.02, 0.02]

## Cor provisória do chão embaixo da grama (até existir o tile de terra).
const GROUND_COLOR: Color = Color("6b4f34")

## Células da camada de lógica: '#' = grama, '.' = terra.
## Sem faixas de 1 tile (GAME_DESIGN §7.1).
const TEST_MASK: Array[String] = [
	"........................",
	"..######.......#####....",
	".#########....#######...",
	".##########..########...",
	"..##########.#######....",
	"...################.....",
	"...###############......",
	"..#################.....",
	"..####...###########....",
	"..###.....##########....",
	"..####...#####...###....",
	"...######.####...####...",
	"....#########....#####..",
	"....######.......#####..",
	"........................",
]


func _initialize() -> void:
	_save(_build_grass_tileset(), GRASS_TILESET_OUT)
	_save(_build_logic_tileset(), LOGIC_TILESET_OUT)
	var terrain: DualGridTerrain = DualGridTerrain.new()
	terrain.display_name = "grama"
	terrain.logic_id = LOGIC_GRASS
	terrain.tile_set = load(GRASS_TILESET_OUT) as TileSet
	terrain.source_id = 0
	terrain.variant_source_id = 1
	for i: int in VARIANT_WEIGHTS.size():
		terrain.variant_coords.append(Vector2i(i, 0))
	terrain.variant_weights = PackedFloat32Array(VARIANT_WEIGHTS)
	_save(terrain, GRASS_TERRAIN_OUT)
	_build_test_scene()
	quit()


func _save(res: Resource, path: String) -> void:
	var err: Error = ResourceSaver.save(res, path)
	print("salvo %s, erro=%d" % [path, err])


func _atlas(png: String, columns: int, rows: int) -> TileSetAtlasSource:
	var source: TileSetAtlasSource = TileSetAtlasSource.new()
	source.texture = load(png) as Texture2D
	source.texture_region_size = Vector2i(T, T)
	for y: int in rows:
		for x: int in columns:
			source.create_tile(Vector2i(x, y))
	return source


func _build_grass_tileset() -> TileSet:
	var tileset: TileSet = TileSet.new()
	tileset.tile_size = Vector2i(T, T)
	tileset.add_source(_atlas(GRASS_PNG, 4, 4), 0)
	tileset.add_source(_atlas(VARIANTS_PNG, VARIANT_WEIGHTS.size(), 1), 1)
	return tileset


func _build_logic_tileset() -> TileSet:
	var tileset: TileSet = TileSet.new()
	tileset.tile_size = Vector2i(T, T)
	tileset.add_source(_atlas(LOGIC_PNG, LOGIC_COUNT, 1), 0)
	return tileset


func _build_test_scene() -> void:
	var w: int = TEST_MASK[0].length()
	var h: int = TEST_MASK.size()

	var region: Node2D = Node2D.new()
	region.name = "RegionGrassTest"
	region.set_script(load(REGION_SCRIPT))
	region.set("bounds", Rect2i(0, 0, w * T, h * T))

	var ground: ColorRect = ColorRect.new()
	ground.name = "GroundPlaceholder"
	ground.color = GROUND_COLOR
	ground.size = Vector2(w * T, h * T)
	ground.mouse_filter = Control.MOUSE_FILTER_IGNORE
	region.add_child(ground)
	ground.owner = region

	var terrain_layer: DualGridLayer = DualGridLayer.new()
	terrain_layer.name = "Terrain"
	terrain_layer.tile_set = load(LOGIC_TILESET_OUT) as TileSet
	terrain_layer.terrains = [load(GRASS_TERRAIN_OUT) as DualGridTerrain]
	for y: int in h:
		for x: int in w:
			var id: int = LOGIC_GRASS if TEST_MASK[y][x] == "#" else LOGIC_GROUND
			terrain_layer.set_cell(Vector2i(x, y), 0, Vector2i(id, 0))
	region.add_child(terrain_layer)
	terrain_layer.owner = region

	var entities: Node2D = Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	region.add_child(entities)
	entities.owner = region

	var spawn: Marker2D = Marker2D.new()
	spawn.name = "Spawn"
	spawn.position = Vector2(w * T, h * T) / 2.0
	region.add_child(spawn)
	spawn.owner = region

	var packed: PackedScene = PackedScene.new()
	packed.pack(region)
	region.free()
	_save(packed, SCENE_OUT)
