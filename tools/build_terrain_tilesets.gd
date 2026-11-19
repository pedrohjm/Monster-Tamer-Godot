extends SceneTree
## Gera os recursos dos terrenos por dual grid e a cena de teste:
##   art/tiles/<terreno>_tileset.tres      atlas 4x4 de cantos (+ variações do tile cheio)
##   art/tiles/<terreno>_terrain.tres      DualGridTerrain
##   art/tiles/terrain_logic_tileset.tres  um tile de cor por terreno (pintar no editor)
##   scenes/world/region_grass_test.tscn   região de teste com um DualGridLayer
##
##   python tools/art/build_terrain_logic.py
##   python tools/art/build_tile_variants.py
##   python tools/art/build_meadow_grass.py
##   python tools/art/build_clearing_dirt.py
##   python tools/art/build_water_assets.py
##   python tools/art/build_beach.py
##   python tools/art/build_mountain_stairs.py
##   python tools/art/build_waterfall.py
##   python tools/art/build_plateau_ridge.py
##   Godot --headless --path . --import
##   Godot --headless --path . -s res://tools/build_terrain_tilesets.gd
##
## As cenas de teste (region_grass_test.tscn e plateau_styles_test.tscn) só são criadas
## quando ainda não existem: você pode pintar nelas no editor sem perder nada. Para
## recriá-las do zero, passe --recriar-cenas:
##   Godot --headless --path . -s res://tools/build_terrain_tilesets.gd -- --recriar-cenas

const T: int = 32
## Fontes extras dentro do TileSet do terreno: margem (embaixo), paredão (tiles altos)
## e borda por cima.
const SHORE_SOURCE: int = 2
const FACE_SOURCE: int = 3
const OVERLAY_SOURCE: int = 4
const LOGIC_PNG: String = "res://art/tiles/terrain_logic.png"
const LOGIC_TILESET_OUT: String = "res://art/tiles/terrain_logic_tileset.tres"
const SCENE_OUT: String = "res://scenes/world/region_grass_test.tscn"
const REGION_SCRIPT: String = "res://scripts/world/region.gd"

## Ids da camada de lógica (coluna em terrain_logic.png).
const LOGIC_DIRT: int = 0
const LOGIC_GRASS: int = 1
const LOGIC_WATER: int = 2
const LOGIC_STONE: int = 3
const LOGIC_SAND: int = 6
const LOGIC_COUNT: int = 8

## Grama do jogo (art/tiles/grass.png) e suas variações (tools/art/build_tile_variants.py):
## misturas, calma, densa e flores.
const GRASS_ATLAS: String = "res://art/tiles/grass.png"
const GRASS_VARIANTS: String = "res://art/tiles/grass_variants.png"
const GRASS_WEIGHTS: Array[float] = [0.04, 0.04, 0.03, 0.015, 0.015, 0.015, 0.04, 0.04, 0.025, 0.015]

## Terrenos em ordem de desenho (o primeiro fica embaixo; ver DualGridLayer).
## `variants`: PNG de uma fileira com as variações do tile cheio e a chance de cada uma.
## `fill`: PNG animado de preenchimento sem bordas (quadros de fill_size tiles lado a lado).
## `shore`: atlas 4x4 que aparece em volta do terreno, embaixo dele (barranco na água).
## `face`: atlas de tiles altos abaixo das bordas sul (paredão).
## `overlay`: atlas 4x4 desenhado por cima do terreno (borda de pedra do planalto).
const TERRAINS: Array[Dictionary] = [
	{
		"name": "water", "display_name": "água", "logic_id": LOGIC_WATER,
		"fill": "res://art/tiles/water.png", "fill_size": Vector2i(6, 5),
		"fill_frames": 16, "fill_frame_seconds": 0.16,
		"overlay": "res://art/tiles/water_shallows.png", "shallow_water_size": Vector2i(6, 5),
	},
	{
		"name": "sand", "display_name": "areia de praia", "logic_id": LOGIC_SAND,
		"atlas": "res://art/tiles/beach_sand.png", "atlas_repeat_size": Vector2i(8, 6),
		"shore": "res://art/tiles/beach_surf.png", "bank_repeat_size": Vector2i(8, 6),
		"bank_neighbor_logic_id": LOGIC_WATER,
	},
	{
		"name": "dirt", "display_name": "terra", "logic_id": LOGIC_DIRT,
		"atlas": "res://art/tiles/clearing_dirt.png", "atlas_repeat_size": Vector2i(8, 6),
		"variants": "res://art/tiles/clearing_dirt_variants.png", "variant_columns": 8,
		# barranco, contorno, linha d'água e sombra (ver tools/art/build_water_assets.py)
		"shore": "res://art/tiles/dirt_shore.png", "bank_repeat_size": Vector2i(4, 3),
		"bank_neighbor_logic_id": LOGIC_WATER,
	},
	{
		"name": "grass", "display_name": "grama", "logic_id": LOGIC_GRASS,
		"atlas": "res://art/tiles/meadow_grass.png", "atlas_repeat_size": Vector2i(6, 4),
		"variants": "res://art/tiles/meadow_grass_variants.png", "variant_columns": 10,
	},
	{
		# Teste: pedra/montanha de outro bioma, por cima da grama (art/tiles/stone.png).
		"name": "stone", "display_name": "pedra", "logic_id": LOGIC_STONE,
		"atlas": "res://art/tiles/stone.png",
	},
]

## Terrenos da camada de planalto (andar 1, GAME_DESIGN §7.1.1): o topo usa a grama.
## Montanha (pincel 5, id 4 na camada de lógica), no formato dual grid da grama. Não entra
## na lista de nenhuma camada: o DualGridLayer a acrescenta sozinho por cima da grama nas
## camadas de chão (ver MOUNTAIN_TERRAIN em scripts/world/dual_grid_layer.gd).
const MOUNTAIN_DEF: Dictionary = {
	"name": "mountain", "display_name": "montanha", "logic_id": 4,
	"stairs": "res://art/tiles/mountain_stairs.png",
	"waterfall": "res://art/tiles/waterfall.png",
	# topo, variações e paredão (ver tools/art/build_mountain_dualgrid.py)
	"atlas": "res://art/tiles/mountain_top.png",
	"variants": "res://art/tiles/mountain_variants.png",
	"variant_weights": [0.10, 0.11, 0.025, 0.06, 0.10, 0.095, 0.10, 0.023, 0.085, 0.028, 0.09, 0.06],
	"face": "res://art/tiles/mountain_face.png", "face_rows": 3, "face_variants": 4,
	"face_clip_table": "res://art/tiles/mountain_face.json", "face_width": 64, "face_all_masks": true, "face_y_sort": true,
}

const PLATEAU_TERRAINS: Array[Dictionary] = [
	{
		"name": "plateau", "display_name": "planalto (grama)", "logic_id": LOGIC_GRASS,
		# grama cortada para dentro da borda de pedra (ver tools/art/build_plateau_ridge.py)
		"atlas": "res://art/tiles/plateau_top.png",
		"variants": GRASS_VARIANTS,
		"variant_weights": GRASS_WEIGHTS,
		# borda de pedra por cima e paredão sul, no estilo de art/tiles/stone.png
		# (ver tools/art/build_plateau_ridge.py)
		"overlay": "res://art/tiles/plateau_ridge.png",
		"face": "res://art/tiles/plateau_face.png", "face_rows": 2, "face_variants": 1,
		"face_above": true, "face_all_masks": true, "face_y_sort": true,
		"tint": Color(1.1, 1.1, 1.04),
	},
]
## Estilos de planalto para comparar (cena scenes/world/plateau_styles_test.tscn).
const STYLES_SCENE_OUT: String = "res://scenes/world/plateau_styles_test.tscn"
const PLATEAU_STYLE_TERRAINS: Array[Dictionary] = [
	{
		# Estilo A: topo e faixa de pedra do estilo B, com o paredão da cartela de IA
		# (ver tools/art/build_plateau_style_a.py).
		"name": "plateau_a", "display_name": "planalto estilo A (cartela)", "logic_id": LOGIC_GRASS,
		"atlas": "res://art/tiles/cliff_grass_b.png",
		"shore": "res://art/tiles/plateau_b_rim.png",
		"face": "res://art/tiles/plateau_a_face.png", "face_rows": 3, "face_variants": 4,
		"face_y_sort": true,
	},
	{
		# Estilo B: tileset de 16 peças com o barranco já desenhado (art/tiles/cliff_grass_b.png)
		# e a continuação do paredão com a base e os tufos (ver tools/art/build_plateau_style_b.py).
		"name": "plateau_b", "display_name": "planalto estilo B (16 peças)", "logic_id": LOGIC_GRASS,
		"bank_material": "res://art/tiles/plateau_b_stone_rim.tres",
		# Sem o shader de emenda de canto (plateau_b_corner_join): nos degraus da borda ele
		# puxava tiras finas de pedra pela lateral dos paredões. A dobra do canto agora vem
		# do próprio atlas do paredão (extend_corner_wraps em build_plateau_style_b.py).
		"atlas": "res://art/tiles/cliff_grass_b.png",
		# um pouco de pedra nas laterais e no norte (ver tools/art/build_plateau_style_b.py)
		"shore": "res://art/tiles/plateau_b_rim.png",
		"face": "res://art/tiles/plateau_b_face.png", "face_rows": 2, "face_variants": 1,
		"face_y_sort": true,
	},
	{
		# Estilo C: paredão de blocos de pedra em colunas, com a grama do jogo no topo
		# (ver tools/art/build_plateau_style_c.py).
		"name": "plateau_c", "display_name": "planalto estilo C (blocos)", "logic_id": LOGIC_GRASS,
		"atlas": GRASS_ATLAS,
		"variants": GRASS_VARIANTS,
		"variant_weights": GRASS_WEIGHTS,
		"shore": "res://art/tiles/plateau_c_rim.png",
		"face": "res://art/tiles/plateau_c_face.png", "face_rows": 3, "face_variants": 2,
		"face_y_sort": true,
		"tint": Color(1.1, 1.1, 1.04),
	},
]
## Mesmo formato para os três (com um recorte de 2 células no sul).
const STYLE_SHAPE: Array[String] = [
	".####.",
	"######",
	"######",
	"##..##",
]
const STYLE_SPACING: int = 7
## Mesma largura da região de teste, para as duas se encaixarem na main.
const STYLE_WIDTH: int = 29
const STYLE_OFFSET: int = 1

## Células da camada de lógica: '#' = grama, '.' = terra, '~' = água, 'S' = pedra, ':' = areia.
## Sem faixas de 1 tile (GAME_DESIGN §7.1).
const TEST_MASK: Array[String] = [
	".............................",
	"..######.......#####.........",
	".#########....#######........",
	".##########..########........",
	"..##########.#######.........",
	"...#####################.....",
	"...######################....",
	"..############:::::::::##....",
	"..####...####::~~~~~~~:##....",
	"..###.....##::~~~~~~~~~##....",
	"..####...##::~~~~~~~~~~~.....",
	"...######.::~~~~~##~~~~~~....",
	"....######::~~~~###~~~~~~....",
	"SSS.######.:~~~~~::~~~~~.....",
	"SSSSSSS.....~~~~~~~~~~~......",
	"SSSSSSSS.....~~~~~~~~~.......",
	"SSSSSS.......................",
]
## Topo dos planaltos na mesma grade: '#' = planalto (grama com borda de pedra e paredão
## sul). O paredão desce ~0,8 tile abaixo das bordas sul: deixe 1 célula livre embaixo delas.
const PLATEAU_MASK: Array[String] = [
	"............................",
	"..#####........#####........",
	".#######......######........",
	".########.....######........",
	"..##..###......####.........",
]
const MASK_IDS: Dictionary = {"#": LOGIC_GRASS, ".": LOGIC_DIRT, "~": LOGIC_WATER, "S": LOGIC_STONE, ":": LOGIC_SAND}


func _initialize() -> void:
	_save(_build_logic_tileset(), LOGIC_TILESET_OUT)
	var terrains: Array[DualGridTerrain] = []
	for def: Dictionary in TERRAINS:
		terrains.append(_build_terrain(def))
	var plateau_terrains: Array[DualGridTerrain] = []
	for def: Dictionary in PLATEAU_TERRAINS:
		plateau_terrains.append(_build_terrain(def))
	_build_terrain(MOUNTAIN_DEF)
	_build_test_scene(terrains, plateau_terrains)
	var styles: Array[DualGridTerrain] = [plateau_terrains[0]]
	for def: Dictionary in PLATEAU_STYLE_TERRAINS:
		styles.append(_build_terrain(def))
	_build_styles_scene(terrains, styles, ["PlateauAtual", "PlateauA", "PlateauB", "PlateauC"])
	quit()


## Cena já existente só é regravada com --recriar-cenas (o usuário pode ter pintado nela).
func _save_scene(packed: PackedScene, path: String) -> void:
	if FileAccess.file_exists(path) and not OS.get_cmdline_user_args().has("--recriar-cenas"):
		print("mantida %s (já existe; use --recriar-cenas para recriar)" % path)
		return
	_save(packed, path)


func _save(res: Resource, path: String) -> void:
	var uid: int = ResourceLoader.get_resource_uid(path) if FileAccess.file_exists(path) else ResourceUID.INVALID_ID
	var err: Error = ResourceSaver.save(res, path)
	if err == OK and uid != ResourceUID.INVALID_ID:
		err = ResourceSaver.set_uid(path, uid)
	print("salvo %s, erro=%d" % [path, err])


func _atlas(png: String, columns: int, rows: int) -> TileSetAtlasSource:
	var source: TileSetAtlasSource = TileSetAtlasSource.new()
	source.texture = load(png) as Texture2D
	source.texture_region_size = Vector2i(T, T)
	for y: int in rows:
		for x: int in columns:
			source.create_tile(Vector2i(x, y))
	return source


func _build_terrain(def: Dictionary) -> DualGridTerrain:
	var weights: Array = def.get("variant_weights", [])
	var repeat_size: Vector2i = def.get("atlas_repeat_size", Vector2i.ONE)
	var bank_size: Vector2i = def.get("bank_repeat_size", Vector2i.ONE)
	var shallow_size: Vector2i = def.get("shallow_water_size", Vector2i.ZERO)
	var clip_lookup := PackedByteArray()
	if def.has("face_clip_table"):
		clip_lookup = PackedByteArray(JSON.parse_string(FileAccess.get_file_as_string(def["face_clip_table"])))
	var tileset: TileSet = TileSet.new()
	tileset.tile_size = Vector2i(T, T)
	if def.has("fill"):
		tileset.add_source(_animated_fill(def), 0)
	else:
		tileset.add_source(_atlas(def["atlas"], 4 * repeat_size.x, 4 * repeat_size.y), 0)
	if def.has("variants"):
		tileset.add_source(_atlas(def["variants"], def.get("variant_columns", weights.size()), 1), 1)
	if def.has("stairs"):
		var stairs := TileSetAtlasSource.new()
		stairs.resource_name = "Escada de pedra"
		stairs.texture_region_size = Vector2i(96, 96)
		stairs.texture = load(def["stairs"]) as Texture2D
		stairs.create_tile(Vector2i.ZERO)
		var data := stairs.get_tile_data(Vector2i.ZERO, 0)
		data.texture_origin = Vector2i(0, -43)
		data.y_sort_origin = 79
		tileset.add_source(stairs, DualGridLayer.STAIRS_SOURCE)
	if def.has("waterfall"):
		tileset.add_source(_waterfall_atlas(def["waterfall"]), DualGridLayer.WATERFALL_SOURCE)
	if def.has("shore"):
		tileset.add_source(_atlas(def["shore"], 4 * bank_size.x, 4 * bank_size.y), SHORE_SOURCE)
	if def.has("face"):
		tileset.add_source(_face_atlas(def, clip_lookup), FACE_SOURCE)
	if def.has("overlay"):
		var overlay_size := shallow_size.max(Vector2i.ONE)
		tileset.add_source(_atlas(def["overlay"], 4 * overlay_size.x, 4 * overlay_size.y), OVERLAY_SOURCE)
	var tileset_path: String = "res://art/tiles/%s_tileset.tres" % def["name"]
	_save(tileset, tileset_path)

	var terrain: DualGridTerrain = DualGridTerrain.new()
	terrain.display_name = def["display_name"]
	terrain.logic_id = def["logic_id"]
	terrain.tile_set = load(tileset_path) as TileSet
	terrain.source_id = 0
	terrain.atlas_repeat_size = repeat_size
	terrain.bank_repeat_size = bank_size
	terrain.bank_neighbor_logic_id = def.get("bank_neighbor_logic_id", -1)
	terrain.shallow_water_size = shallow_size
	terrain.variant_source_id = 1
	for i: int in weights.size():
		terrain.variant_coords.append(Vector2i(i, 0))
	terrain.variant_weights = PackedFloat32Array(weights)
	if def.has("fill"):
		terrain.fill_coords = Vector2i.ZERO
		terrain.fill_size = def["fill_size"]
	if def.has("shore"):
		terrain.bank_source_id = SHORE_SOURCE
	if def.has("bank_material"):
		terrain.bank_material = load(def["bank_material"]) as Material
	if def.has("face_material"):
		terrain.face_material = load(def["face_material"]) as Material
	if def.has("face"):
		terrain.face_source_id = FACE_SOURCE
		terrain.face_clip_lookup = clip_lookup
		terrain.face_rows = def["face_rows"]
		terrain.face_variants = def["face_variants"]
		terrain.face_above = def.get("face_above", false)
		terrain.face_all_masks = def.get("face_all_masks", false)
		terrain.face_y_sort = def.get("face_y_sort", false)
	if def.has("overlay"):
		terrain.overlay_source_id = OVERLAY_SOURCE
	terrain.tint = def.get("tint", Color.WHITE)
	var terrain_path: String = "res://art/tiles/%s_terrain.tres" % def["name"]
	_save(terrain, terrain_path)
	return load(terrain_path) as DualGridTerrain


## Tiles altos (1 x face_rows células): só as máscaras com borda sul, ou todas as parciais
## com `face_all_masks`. O Godot centraliza um tile maior que a célula; texture_origin o
## desce para o topo ficar na célula. y_sort_origin fica na base do paredão (última linha
## opaca do tile), medida a partir do centro da célula.
func _face_atlas(def: Dictionary, clip_lookup: PackedByteArray) -> TileSetAtlasSource:
	var rows: int = def["face_rows"]
	var source: TileSetAtlasSource = TileSetAtlasSource.new()
	source.texture = load(def["face"]) as Texture2D
	var width: int = def.get("face_width", T)
	source.texture_region_size = Vector2i(width, T)
	# Direto do arquivo: no modo headless a textura importada não devolve a imagem.
	var image: Image = Image.load_from_file(ProjectSettings.globalize_path(def["face"]))
	for v: int in def["face_variants"]:
		for m: int in 16:
			var wanted: bool = DualGrid.has_south_edge(m)
			if def.get("face_all_masks", false):
				wanted = m != DualGrid.EMPTY_MASK and m != DualGrid.FULL_MASK
			if not wanted:
				continue
			var coords: Vector2i = DualGrid.face_coords(m, Vector2i(v, 0), rows, def["face_variants"])
			_add_face_tile(source, image, coords, rows, width)
	var groups: int = 0
	for group: int in clip_lookup:
		groups = maxi(group, groups)
	for group in groups:
		for variant in int(def["face_variants"]):
			var coords := Vector2i((group % 4) * 4 + variant, (4 + group / 4) * rows)
			_add_face_tile(source, image, coords, rows, width)
	return source


func _add_face_tile(source: TileSetAtlasSource, image: Image, coords: Vector2i, rows: int, width: int) -> void:
	source.create_tile(coords, Vector2i(1, rows))
	var data := source.get_tile_data(coords, 0)
	data.texture_origin = Vector2i((T - width) / 2, -(rows - 1) * T / 2)
	data.y_sort_origin = _face_base(image, coords, rows, width) - T / 2


## Última linha com pixel opaco de verdade (alfa 1, a pedra) no tile alto; sem pedra
## (só sombra), o centro da célula.
func _face_base(image: Image, coords: Vector2i, rows: int, width: int) -> int:
	var base: int = T / 2
	for y: int in rows * T:
		for x: int in width:
			if image.get_pixel(coords.x * width + x, coords.y * T + y).a > 0.99:
				base = maxi(base, y)
	return base


## As quatro linhas da queda são peça isolada, ponta esquerda, centro e ponta direita.
func _waterfall_atlas(path: String) -> TileSetAtlasSource:
	var source := TileSetAtlasSource.new()
	source.resource_name = "Cachoeira"
	source.texture = load(path) as Texture2D
	source.texture_region_size = Vector2i(160, 144)
	var frames := source.texture.get_width() / source.texture_region_size.x
	for row in 4:
		var tile := Vector2i(0, row)
		source.create_tile(tile)
		source.set_tile_animation_columns(tile, frames)
		source.set_tile_animation_frames_count(tile, frames)
		for frame in frames:
			source.set_tile_animation_frame_duration(tile, frame, 0.075)
		var data := source.get_tile_data(tile, 0)
		data.texture_origin = Vector2i(0, -36)
		data.y_sort_origin = 86
	return source


## Bloco de fill_size tiles animado: cada quadro é um bloco inteiro ao lado do anterior,
## então os quadros de um tile ficam a fill_size.x - 1 tiles de distância.
func _animated_fill(def: Dictionary) -> TileSetAtlasSource:
	var size: Vector2i = def["fill_size"]
	var frames: int = def["fill_frames"]
	var source: TileSetAtlasSource = TileSetAtlasSource.new()
	source.texture = load(def["fill"]) as Texture2D
	source.texture_region_size = Vector2i(T, T)
	for y: int in size.y:
		for x: int in size.x:
			var coords: Vector2i = Vector2i(x, y)
			source.create_tile(coords)
			source.set_tile_animation_separation(coords, Vector2i(size.x - 1, 0))
			source.set_tile_animation_columns(coords, 0)
			source.set_tile_animation_frames_count(coords, frames)
			for f: int in frames:
				source.set_tile_animation_frame_duration(coords, f, def["fill_frame_seconds"])
	return source


## Cena de comparação: chão de grama e o mesmo planalto em cada estilo, lado a lado.
func _build_styles_scene(terrains: Array[DualGridTerrain], styles: Array[DualGridTerrain], names: Array[String]) -> void:
	var w: int = STYLE_WIDTH
	var h: int = STYLE_SHAPE.size() + 6
	var region: Node2D = Node2D.new()
	region.name = "PlateauStylesTest"
	region.set_script(load(REGION_SCRIPT))
	region.set("bounds", Rect2i(T / 2, T / 2, (w - 1) * T, (h - 1) * T))
	region.y_sort_enabled = true

	var ground: DualGridLayer = DualGridLayer.new()
	ground.name = "Terrain"
	ground.tile_set = load(LOGIC_TILESET_OUT) as TileSet
	ground.terrains = terrains
	ground.z_index = -2
	ground.self_modulate = Color(1, 1, 1, ground.logic_opacity_in_editor)
	for y: int in h:
		for x: int in w:
			ground.set_cell(Vector2i(x, y), 0, Vector2i(LOGIC_GRASS, 0))
	region.add_child(ground)
	ground.owner = region

	for i: int in styles.size():
		var layer: DualGridLayer = DualGridLayer.new()
		layer.name = names[i]
		layer.tile_set = ground.tile_set
		layer.terrains = [styles[i]]
		layer.self_modulate = ground.self_modulate
		layer.y_sort_enabled = true
		layer.floor_z_index = -1
		for y: int in STYLE_SHAPE.size():
			for x: int in STYLE_SHAPE[y].length():
				if STYLE_SHAPE[y][x] == "#":
					layer.set_cell(Vector2i(STYLE_OFFSET + i * STYLE_SPACING + x, 1 + y), 0, Vector2i(LOGIC_GRASS, 0))
		region.add_child(layer)
		layer.owner = region

	var entities: Node2D = Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	region.add_child(entities)
	entities.owner = region

	# Ponto de partida: na frente do planalto do meio.
	var spawn: Marker2D = Marker2D.new()
	spawn.name = "Spawn"
	spawn.position = Vector2((STYLE_OFFSET + STYLE_SPACING * 2) * T, (STYLE_SHAPE.size() + 3) * T)
	region.add_child(spawn)
	spawn.owner = region

	var packed: PackedScene = PackedScene.new()
	packed.pack(region)
	region.free()
	_save_scene(packed, STYLES_SCENE_OUT)


func _build_logic_tileset() -> TileSet:
	var tileset: TileSet = TileSet.new()
	tileset.tile_size = Vector2i(T, T)
	tileset.add_source(_atlas(LOGIC_PNG, LOGIC_COUNT, 1), 0)
	return tileset


func _build_test_scene(terrains: Array[DualGridTerrain], plateau_terrains: Array[DualGridTerrain]) -> void:
	var w: int = TEST_MASK[0].length()
	var h: int = TEST_MASK.size()

	var region: Node2D = Node2D.new()
	region.name = "RegionGrassTest"
	region.set_script(load(REGION_SCRIPT))
	# Meio tile para dentro: a borda do terreno pintado fica fora da câmera.
	region.set("bounds", Rect2i(T / 2, T / 2, (w - 1) * T, (h - 1) * T))
	# Paredões, personagens e props se ordenam por Y juntos; o chão fica embaixo por z_index.
	region.y_sort_enabled = true

	var terrain_layer: DualGridLayer = DualGridLayer.new()
	terrain_layer.name = "Terrain"
	terrain_layer.tile_set = load(LOGIC_TILESET_OUT) as TileSet
	terrain_layer.terrains = terrains
	terrain_layer.z_index = -2
	# Mesmo valor que o DualGridLayer aplica no editor (não marca a cena como alterada).
	terrain_layer.self_modulate = Color(1, 1, 1, terrain_layer.logic_opacity_in_editor)
	for y: int in h:
		for x: int in w:
			var id: int = MASK_IDS[TEST_MASK[y][x]]
			terrain_layer.set_cell(Vector2i(x, y), 0, Vector2i(id, 0))
	region.add_child(terrain_layer)
	terrain_layer.owner = region

	var plateau: DualGridLayer = DualGridLayer.new()
	plateau.name = "Plateau"
	plateau.tile_set = terrain_layer.tile_set
	plateau.terrains = plateau_terrains
	plateau.self_modulate = terrain_layer.self_modulate
	plateau.y_sort_enabled = true
	plateau.floor_z_index = -1
	for y: int in PLATEAU_MASK.size():
		for x: int in PLATEAU_MASK[y].length():
			if PLATEAU_MASK[y][x] == "#":
				plateau.set_cell(Vector2i(x, y), 0, Vector2i(LOGIC_GRASS, 0))
	region.add_child(plateau)
	plateau.owner = region

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
	_save_scene(packed, SCENE_OUT)
