extends SceneTree
## Gera o TileSet, as cenas de props e a cena de uma região a partir do mapa ASCII
## em tools/maps/. Rodar depois do script de arte do bioma (tools/art/build_*_assets.py):
##   Godot --headless --path . --import
##   Godot --headless --path . -s res://tools/build_region.gd -- [jungle|desert]
## Sem argumento, gera a selva. A cena gerada é sobrescrita a cada execução: edite o
## mapa .txt, não a cena.

const T: int = 32
const PROPS_TEX_DIR: String = "res://art/sprites/props"
const PROPS_SCENE_DIR: String = "res://scenes/props"
const REGION_SCRIPT: String = "res://scripts/world/region.gd"

## Configuração por bioma. `rank`: letra do terreno -> rank do vértice (letra ausente =
## `default_rank`). `faces`: letras da frente do penhasco que viram um segmento próprio
## centralizado nas células ([nome do segmento, bloqueia]). `sand_base`: troca a frente
## por `base_sand` quando o chão abaixo é areia.
const BIOMES: Dictionary = {
	"jungle": {
		"atlas_png": "res://art/tiles/jungle_terrain.png",
		"atlas_json": "res://art/tiles/jungle_terrain.json",
		"tileset_out": "res://art/tiles/jungle_tileset.tres",
		"map": "res://tools/maps/region_jungle_00.txt",
		"region_out": "res://scenes/world/region_jungle_00.tscn",
		"node_name": "RegionJungle00",
		"cliff_dir": "res://art/sprites/cliffs",
		"rank": {"~": 0, "=": 0, "-": 1, ".": 2, ",": 3, ":": 3},
		"default_rank": 4,
		"faces": {"S": ["stairs", false], "C": ["cave", true]},
		"sand_base": true,
		"open_edges": ["right"],  # deserto à direita
		"props": {
			"p": ["palm_a"], "q": ["palm_b"], "b": ["banyan"], "r": ["jungle_tree"],
			"t": ["tent"], "c": ["campfire"], "k": ["barrel"], "x": ["crate"], "s": ["sign"],
			"l": ["log"], "u": ["bush"], "n": ["fern_a", "fern_b", "fern_c"], "m": ["mushrooms"],
			"o": ["rock_small"], "w": ["rock_wall_0", "rock_wall_1", "rock_wall_2", "rock_wall_3"],
			"f": ["flowers_pink", "flowers_orange", "flowers_red", "flowers_purple", "flowers_white"],
		},
	},
	"desert": {
		"atlas_png": "res://art/tiles/desert_terrain.png",
		"atlas_json": "res://art/tiles/desert_terrain.json",
		"tileset_out": "res://art/tiles/desert_tileset.tres",
		"map": "res://tools/maps/region_desert_00.txt",
		"region_out": "res://scenes/world/region_desert_00.tscn",
		"node_name": "RegionDesert00",
		"cliff_dir": "res://art/sprites/cliffs_desert",
		"rank": {"~": 0, "=": 0, "-": 1, ".": 2, ",": 3, ":": 3, "g": 4, "T": 4},
		"default_rank": 2,
		"faces": {"S": ["stairs", false], "C": ["cave", true], "R": ["temple", true]},
		"sand_base": false,
		"open_edges": ["left"],  # selva à esquerda
		"props": {
			"p": ["palm_a"], "q": ["palm_b"], "r": ["jungle_tree"], "v": ["blossom_tree"],
			"u": ["bush"], "n": ["fern_a", "fern_b", "fern_c"], "o": ["rock_small"],
			"f": ["flowers_pink", "flowers_orange", "flowers_red", "flowers_purple", "flowers_white"],
			"k": ["cactus_tall", "cactus_short"], "b": ["cactus_barrel"], "e": ["cactus_pear"],
			"d": ["dead_tree"], "h": ["dry_bush"], "y": ["dry_grass_0", "dry_grass_1", "dry_grass_2"],
			"a": ["sand_rock"], "B": ["sand_boulder"], "A": ["sand_arch"],
			"i": ["ruin_pillar_tall", "ruin_pillar_short"], "G": ["ruin_gate"], "j": ["clay_pot"],
			"z": ["brazier"], "x": ["fence"], "L": ["lamp_post"],
			"w": ["sandstone_wall_0", "sandstone_wall_1", "sandstone_wall_2", "sandstone_wall_3"],
		},
	},
}
## Quanto do segmento de penhasco (px) sobe por cima da última linha do planalto.
const CLIFF_RIM: int = 22
## Sobreposição (px) entre segmentos vizinhos para não aparecer fresta.
const CLIFF_OVERLAP: int = 6
## Laterais: passo vertical (px) entre pedaços de rocha e deslocamento máximo para os lados.
const SIDE_STEP: int = 40
const SIDE_JITTER: int = 3
## Quanto o canto interno avança (px) para dentro da célula do planalto vizinho.
const INNER_INSET: int = 12
const FRONT_VARIANTS: Array[String] = ["front_0", "front_1", "front_2", "front_3"]

## Camadas de terreno de baixo para cima: nome no atlas e rank mínimo do vértice.
const LAYERS: Array[Array] = [["shallow", 1], ["sand", 2], ["dirt", 3], ["grass", 4]]
const LAYER_COLORS: Array[Color] = [Color.AQUAMARINE, Color.SANDY_BROWN, Color.SADDLE_BROWN, Color.FOREST_GREEN]
const FRAME_SECONDS: float = 0.35
const VARIANT_CHANCE: float = 0.3

## Props: raio do círculo de colisão (float) ou tamanho da caixa (Vector2); null = decoração.
const PROP_DEFS: Dictionary = {
	"palm_a": 6.0, "palm_b": 6.0, "banyan": 14.0, "jungle_tree": 9.0,
	"tent": Vector2(50, 14), "campfire": 8.0, "barrel": 7.0, "crate": Vector2(18, 10),
	"sign": Vector2(14, 6), "log": Vector2(44, 10), "rock_small": Vector2(20, 8), "bush": 9.0,
	"fern_a": null, "fern_b": null, "fern_c": null, "mushrooms": null,
	"flowers_pink": null, "flowers_orange": null, "flowers_red": null,
	"flowers_purple": null, "flowers_white": null,
	"rock_wall_0": Vector2(30, 12), "rock_wall_1": Vector2(30, 12),
	"rock_wall_2": Vector2(30, 12), "rock_wall_3": Vector2(30, 12),
	"tall_grass_0": null, "tall_grass_1": null, "tall_grass_2": null, "tall_grass_3": null,
	# Deserto. Array = várias caixas Rect2(centro_x, centro_y em relação aos pés, largura, altura).
	"cactus_tall": 5.0, "cactus_short": 5.0, "cactus_barrel": 7.0, "cactus_pear": 9.0,
	"dead_tree": 5.0, "dry_bush": 8.0, "blossom_tree": 9.0,
	"dry_grass_0": null, "dry_grass_1": null, "dry_grass_2": null,
	"sand_rock": Vector2(20, 8), "sand_boulder": Vector2(36, 14),
	"sand_arch": [Rect2(-50, -7, 24, 14), Rect2(50, -7, 24, 14)],
	"ruin_pillar_tall": Vector2(16, 8), "ruin_pillar_short": Vector2(16, 8),
	"ruin_gate": [Rect2(-22, -4, 18, 8), Rect2(22, -4, 18, 8)],
	"clay_pot": 5.0, "brazier": 6.0, "fence": Vector2(36, 6), "lamp_post": [Rect2(-5, -2, 10, 4)],
	"sandstone_wall_0": Vector2(30, 12), "sandstone_wall_1": Vector2(30, 12),
	"sandstone_wall_2": Vector2(30, 12), "sandstone_wall_3": Vector2(30, 12),
}
var cfg: Dictionary
var layout: Dictionary
var terrain: PackedStringArray
var props: PackedStringArray
var width: int
var height: int


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var biome: String = args[0] if args.size() > 0 else "jungle"
	if not BIOMES.has(biome):
		push_error("bioma desconhecido: %s (use %s)" % [biome, ", ".join(BIOMES.keys())])
		quit(1)
		return
	cfg = BIOMES[biome]
	layout = JSON.parse_string(FileAccess.get_file_as_string(cfg["atlas_json"]))
	if not _read_map():
		quit(1)
		return
	var tileset: TileSet = _build_tileset()
	var err: Error = ResourceSaver.save(tileset, cfg["tileset_out"])
	assert(err == OK)
	tileset = load(cfg["tileset_out"])
	var scenes: Dictionary = _build_prop_scenes()
	var region: Node2D = _build_region(tileset, scenes)
	var packed: PackedScene = PackedScene.new()
	packed.pack(region)
	err = ResourceSaver.save(packed, cfg["region_out"])
	print("região salva em %s (%dx%d), erro=%d" % [cfg["region_out"], width, height, err])
	region.free()
	quit(0 if err == OK else 1)


# ------------------------------------------------------------------ mapa

func _read_map() -> bool:
	var blocks: Array[PackedStringArray] = [PackedStringArray()]
	for line: String in FileAccess.get_file_as_string(cfg["map"]).split("\n"):
		line = line.strip_edges(false, true)
		if line.begins_with("#"):
			continue
		if line.is_empty():
			if not blocks[-1].is_empty():
				blocks.append(PackedStringArray())
			continue
		blocks[-1].append(line)
	terrain = blocks[0]
	props = blocks[1] if blocks.size() > 1 else PackedStringArray()
	height = terrain.size()
	width = terrain[0].length()
	for i: int in terrain.size():
		if terrain[i].length() != width:
			push_error("linha %d do terreno tem %d colunas (esperado %d)" % [i, terrain[i].length(), width])
			return false
	return true


func _ch(x: int, y: int) -> String:
	return terrain[clampi(y, 0, height - 1)][clampi(x, 0, width - 1)]


func _prop(x: int, y: int) -> String:
	if y < 0 or y >= props.size() or x < 0 or x >= props[y].length():
		return "."
	return props[y][x]


func _rank(x: int, y: int) -> int:
	return (cfg["rank"] as Dictionary).get(_ch(x, y), cfg["default_rank"])


## Borda ligada a outra região: sem bloqueio de colisão nela.
func _open(side: String) -> bool:
	return (cfg.get("open_edges", []) as Array).has(side)


func _is_face(c: String) -> bool:
	return c == "F" or (cfg["faces"] as Dictionary).has(c)


func _is_plateau(c: String) -> bool:
	return c == "P" or c == ":"


func _hash(x: int, y: int, salt: int = 0) -> int:
	return absi(hash(Vector3i(x, y, salt)))


# ------------------------------------------------------------------ tileset

func _build_tileset() -> TileSet:
	var ts: TileSet = TileSet.new()
	ts.tile_size = Vector2i(T, T)
	ts.add_physics_layer()
	ts.set_physics_layer_collision_layer(0, 1)
	ts.set_physics_layer_collision_mask(0, 0)
	var src: TileSetAtlasSource = TileSetAtlasSource.new()
	src.texture = load(cfg["atlas_png"])
	src.texture_region_size = Vector2i(T, T)
	ts.add_source(src, 0)

	var frames: int = layout["frames"]
	_create_tile(src, _v(layout["deep_water"]["coords"]), frames)

	var corner_bits: Array[TileSet.CellNeighbor] = [
		TileSet.CELL_NEIGHBOR_TOP_LEFT_CORNER, TileSet.CELL_NEIGHBOR_TOP_RIGHT_CORNER,
		TileSet.CELL_NEIGHBOR_BOTTOM_LEFT_CORNER, TileSet.CELL_NEIGHBOR_BOTTOM_RIGHT_CORNER,
	]
	for i: int in LAYERS.size():
		var name: String = LAYERS[i][0]
		var info: Dictionary = layout["layers"][name]
		ts.add_terrain_set()
		ts.set_terrain_set_mode(i, TileSet.TERRAIN_MODE_MATCH_CORNERS)
		ts.add_terrain(i)
		ts.set_terrain_name(i, 0, name)
		ts.set_terrain_color(i, 0, LAYER_COLORS[i])
		var row: int = info["row"]
		var coords_list: Array[Vector2i] = []
		var bits_list: Array[int] = []
		for bits: int in range(1, 16):
			coords_list.append(Vector2i(bits, row))
			bits_list.append(bits)
		for v: Array in info["variants"]:
			coords_list.append(_v(v))
			bits_list.append(15)
		for j: int in coords_list.size():
			var animated: bool = info["animated"] and j < 15
			_create_tile(src, coords_list[j], frames if animated else 1)
			var td: TileData = src.get_tile_data(coords_list[j], 0)
			td.terrain_set = i
			td.terrain = 0
			for b: int in 4:
				if bits_list[j] & (1 << b):
					td.set_terrain_peering_bit(corner_bits[b], 0)
			if j >= 15:
				td.probability = VARIANT_CHANCE

	var blocker: Vector2i = _v(layout["blocker"])
	_create_tile(src, blocker, 1)
	var bd: TileData = src.get_tile_data(blocker, 0)
	bd.add_collision_polygon(0)
	var h: float = T / 2.0
	bd.set_collision_polygon_points(0, 0, PackedVector2Array([Vector2(-h, -h), Vector2(h, -h), Vector2(h, h), Vector2(-h, h)]))
	return ts


func _create_tile(src: TileSetAtlasSource, coords: Vector2i, frames: int) -> void:
	src.create_tile(coords)
	if frames > 1:
		src.set_tile_animation_columns(coords, 1)
		src.set_tile_animation_frames_count(coords, frames)
		for f: int in frames:
			src.set_tile_animation_frame_duration(coords, f, FRAME_SECONDS)


func _v(a: Array) -> Vector2i:
	return Vector2i(int(a[0]), int(a[1]))


# ------------------------------------------------------------------ props

func _build_prop_scenes() -> Dictionary:
	DirAccess.make_dir_recursive_absolute(PROPS_SCENE_DIR)
	var scenes: Dictionary = {}
	var used: Dictionary = {}
	for options: Array in (cfg["props"] as Dictionary).values():
		for n: String in options:
			used[n] = true
	for i: int in 4:
		used["tall_grass_%d" % i] = true
	for name: String in used:
		var tex: Texture2D = load("%s/%s.png" % [PROPS_TEX_DIR, name])
		var shape_def: Variant = PROP_DEFS[name]
		var root: Node2D
		if shape_def == null:
			root = Node2D.new()
		else:
			root = StaticBody2D.new()
			(root as StaticBody2D).collision_mask = 0
		root.name = name.to_pascal_case()
		var sprite: Sprite2D = Sprite2D.new()
		sprite.name = "Sprite"
		sprite.texture = tex
		sprite.offset = Vector2(0, -tex.get_height() / 2.0)
		root.add_child(sprite)
		sprite.owner = root
		if shape_def is Array:
			for k: int in (shape_def as Array).size():
				var r: Rect2 = shape_def[k]
				var box: CollisionShape2D = CollisionShape2D.new()
				box.name = "Collision%d" % k
				var rs: RectangleShape2D = RectangleShape2D.new()
				rs.size = r.size
				box.shape = rs
				box.position = r.position
				root.add_child(box)
				box.owner = root
		elif shape_def != null:
			var col: CollisionShape2D = CollisionShape2D.new()
			col.name = "Collision"
			if shape_def is float:
				var circle: CircleShape2D = CircleShape2D.new()
				circle.radius = shape_def
				col.shape = circle
				col.position = Vector2(0, -shape_def * 0.6)
			else:
				var rect: RectangleShape2D = RectangleShape2D.new()
				rect.size = shape_def
				col.shape = rect
				col.position = Vector2(0, -(shape_def as Vector2).y / 2.0)
			root.add_child(col)
			col.owner = root
		var packed: PackedScene = PackedScene.new()
		packed.pack(root)
		var path: String = "%s/%s.tscn" % [PROPS_SCENE_DIR, name]
		ResourceSaver.save(packed, path)
		root.free()
		scenes[name] = load(path)
	return scenes


# ------------------------------------------------------------------ região

func _build_region(tileset: TileSet, scenes: Dictionary) -> Node2D:
	var root: Node2D = Node2D.new()
	root.name = cfg["node_name"]
	root.set_script(load(REGION_SCRIPT))
	root.set("bounds", Rect2i(0, 0, width * T, height * T))

	var ground: Node2D = _add(root, Node2D.new(), "Ground")
	var deep: TileMapLayer = _tile_layer(ground, tileset, "DeepWater", Vector2(T / 2.0, T / 2.0))
	var layers: Array[TileMapLayer] = []
	for l: Array in LAYERS:
		layers.append(_tile_layer(ground, tileset, (l[0] as String).capitalize(), Vector2(T / 2.0, T / 2.0)))
	var decor: Node2D = _add(ground, Node2D.new(), "GroundDecor")
	var cliffs: Node2D = _add(ground, Node2D.new(), "Cliffs")
	var entities: Node2D = _add(root, Node2D.new(), "Entities")
	entities.y_sort_enabled = true
	var collision: TileMapLayer = _tile_layer(root, tileset, "Collision", Vector2.ZERO)
	collision.visible = false

	# Terreno: tile (x, y) usa os vértices (x..x+1, y..y+1) e fica deslocado meio tile.
	var deep_coords: Vector2i = _v(layout["deep_water"]["coords"])
	# Numa borda aberta à esquerda/em cima, a coluna/linha -1 (meio tile para fora) fica
	# para a região vizinha, que já desenha meio tile além da própria borda.
	var x_from: int = 0 if _open("left") else -1
	var y_from: int = 0 if _open("top") else -1
	for y: int in range(y_from, height):
		for x: int in range(x_from, width):
			for i: int in LAYERS.size():
				var min_rank: int = LAYERS[i][1]
				var bits: int = 0
				if _rank(x, y) >= min_rank: bits |= 1
				if _rank(x + 1, y) >= min_rank: bits |= 2
				if _rank(x, y + 1) >= min_rank: bits |= 4
				if _rank(x + 1, y + 1) >= min_rank: bits |= 8
				if i == 0 and bits != 15:
					deep.set_cell(Vector2i(x, y), 0, deep_coords)
				if bits == 0:
					continue
				var info: Dictionary = layout["layers"][LAYERS[i][0]]
				var coords: Vector2i = Vector2i(bits, info["row"])
				var variants: Array = info["variants"]
				if bits == 15 and not variants.is_empty() and (_hash(x, y, i) % 100) < VARIANT_CHANCE * 100:
					coords = _v(variants[_hash(x, y, i + 7) % variants.size()])
				layers[i].set_cell(Vector2i(x, y), 0, coords)

	# Células: penhascos, colisão, escadas, caverna, pontes, mato alto e props.
	var blocker: Vector2i = _v(layout["blocker"])
	for y: int in range(-1, height + 1):
		for x: int in range(-1, width + 1):
			if x < 0 or y < 0 or x >= width or y >= height:
				var side_open: bool = (x < 0 and _open("left")) or (x >= width and _open("right")) \
						or (y < 0 and _open("top")) or (y >= height and _open("bottom"))
				if not side_open:
					collision.set_cell(Vector2i(x, y), 0, blocker)
				continue
			var c: String = terrain[y][x]
			var faces: Dictionary = cfg["faces"]
			if c == "~" or c == "-" or c == "F" or (faces.has(c) and faces[c][1]):
				collision.set_cell(Vector2i(x, y), 0, blocker)
			if c == "=" and _ch(x - 1, y) != "=":
				_add_bridge(decor, x, y)
			if c == "T":
				_add_prop(root, entities, scenes, "tall_grass_%d" % (_hash(x, y, 3) % 4), x, y, 4)
			var p: String = _prop(x, y)
			var prop_chars: Dictionary = cfg["props"]
			if p == "@":
				var spawn: Marker2D = _add(root, Marker2D.new(), "Spawn")
				spawn.position = Vector2(x * T + T / 2.0, y * T + T / 2.0)
				spawn.owner = root
			elif prop_chars.has(p):
				var options: Array = prop_chars[p]
				_add_prop(root, entities, scenes, options[_hash(x, y, 5) % options.size()], x, y, 2)
	for n: Node in [ground, deep, cliffs, decor, entities, collision] + layers:
		n.owner = root
	_build_cliffs(cliffs)
	for n: Node in decor.get_children() + cliffs.get_children():
		n.owner = root
	return root


# ------------------------------------------------------------------ penhascos

## Monta a borda do planalto com os segmentos grandes de art/sprites/cliffs.
## Laterais: colunas `F` com planalto ao lado. Frente: linhas `F`/`S`/`C` logo abaixo do
## planalto, com canto onde encontra uma lateral, ponta onde termina solta, escada e
## caverna centralizadas nas células `S` e `C`, e segmentos retos sorteados no resto.
func _build_cliffs(node: Node2D) -> void:
	# Laterais: pedaços de rocha sobrepostos de cima para baixo, com leve deslocamento.
	for x: int in width:
		for y: int in height:
			if not _is_side_cell(x, y) or (y > 0 and _is_side_cell(x, y - 1)):
				continue
			var y_end: int = y
			while y_end + 1 < height and _is_side_cell(x, y_end + 1):
				y_end += 1
			var plateau_right: bool = _is_plateau(_ch(x + 1, y))
			var name: String = "side_L" if plateau_right else "side_R"
			var size: Vector2i = _cliff_size(name)
			var top: int = y * T - (CLIFF_RIM if y > 0 else 0)
			var bottom: int = (y_end + 1) * T - size.y + CLIFF_RIM
			var count: int = maxi(1, ceili(float(bottom - top) / SIDE_STEP) + 1)
			for i: int in count:
				var py: int = top + roundi(float(bottom - top) * i / maxi(1, count - 1))
				var jitter: int = (_hash(x, py, 13) % (2 * SIDE_JITTER + 1)) - SIDE_JITTER
				var left: int = (x + 1) * T - size.x + jitter if plateau_right else x * T + jitter
				_cliff_sprite(node, name, left, py)

	for y: int in height:
		var x: int = 0
		while x < width:
			if not _is_front(x, y):
				x += 1
				continue
			var x1: int = x
			while x1 + 1 < width and _is_front(x1 + 1, y):
				x1 += 1
			_build_front_run(node, x, x1, y)
			x = x1 + 1


func _build_front_run(node: Node2D, x0: int, x1: int, y: int) -> void:
	var top: int = y * T - CLIFF_RIM
	var caps: Array[Array] = []  # [nome, esquerda_px], desenhados por cima dos retos
	var fill_from: int
	var fill_to: int
	if _is_plateau(_ch(x0 - 1, y)) and x0 > 0:
		var left: int = x0 * T - INNER_INSET
		caps.append(["inner_L", left])
		fill_from = left + _cliff_size("inner_L").x - CLIFF_OVERLAP
	elif (_ch(x0 - 1, y) == "F" or _ch(x0 - 1, y - 1) == "F") and x0 > 0:
		var left: int = x0 * T - _cliff_size("side_L").x
		caps.append(["corner_L", left])
		fill_from = left + _cliff_size("corner_L").x - CLIFF_OVERLAP
	else:
		caps.append(["end_L", x0 * T])
		fill_from = x0 * T + _cliff_size("end_L").x - CLIFF_OVERLAP
	if _is_plateau(_ch(x1 + 1, y)) and x1 + 1 < width:
		var left: int = (x1 + 1) * T + INNER_INSET - _cliff_size("inner_R").x
		caps.append(["inner_R", left])
		fill_to = left + CLIFF_OVERLAP
	elif (_ch(x1 + 1, y) == "F" or _ch(x1 + 1, y - 1) == "F") and x1 + 1 < width:
		var right: int = (x1 + 1) * T + _cliff_size("side_R").x
		var left: int = right - _cliff_size("corner_R").x
		caps.append(["corner_R", left])
		fill_to = left + CLIFF_OVERLAP
	else:
		var left: int = (x1 + 1) * T - _cliff_size("end_R").x
		caps.append(["end_R", left])
		fill_to = left + CLIFF_OVERLAP

	var gaps: Array[Vector2i] = []
	var cursor: int = fill_from
	var x: int = x0
	while x <= x1:
		var c: String = terrain[y][x]
		if not (cfg["faces"] as Dictionary).has(c):
			x += 1
			continue
		var s1: int = x
		while s1 + 1 <= x1 and terrain[y][s1 + 1] == c:
			s1 += 1
		var name: String = cfg["faces"][c][0]
		var w: int = _cliff_size(name).x
		var left: int = int((x + s1 + 1) * T / 2.0 - w / 2.0)
		caps.append([name, left])
		gaps.append(Vector2i(cursor, left + CLIFF_OVERLAP))
		cursor = left + w - CLIFF_OVERLAP
		x = s1 + 1
	gaps.append(Vector2i(cursor, fill_to))

	for gap: Vector2i in gaps:
		var span: int = gap.y - gap.x
		if span <= 0:
			continue
		var seg_w: int = _cliff_size("front_0").x
		var count: int = maxi(1, ceili(float(span) / (seg_w - CLIFF_OVERLAP)))
		var step: float = 0.0 if count == 1 else float(span - seg_w) / (count - 1)
		for i: int in count:
			var left: int = gap.x + roundi(i * step) if count > 1 else gap.x + (span - seg_w) / 2
			var cell_x: int = clampi((left + seg_w / 2) / T, 0, width - 1)
			var below: String = _ch(cell_x, y + 2)
			var name: String = FRONT_VARIANTS[_hash(cell_x, y, 11) % FRONT_VARIANTS.size()]
			if below == "." and cfg["sand_base"]:
				name = "base_sand"
			elif below == "~" or below == "-":
				name = "base_water"
			_cliff_sprite(node, name, left, top)
	for cap: Array in caps:
		_cliff_sprite(node, cap[0], cap[1], top)


## Célula `F` ao lado do planalto que não faz parte de um paredão frontal.
func _is_side_cell(x: int, y: int) -> bool:
	if terrain[y][x] != "F" or not (_is_plateau(_ch(x + 1, y)) or _is_plateau(_ch(x - 1, y))):
		return false
	return not (_is_plateau(_ch(x, y - 1)) or _is_plateau(_ch(x, y - 2)))


func _is_front(x: int, y: int) -> bool:
	return _is_face(terrain[y][x]) and _is_plateau(_ch(x, y - 1)) and y > 0


func _cliff_size(name: String) -> Vector2i:
	return _v(layout["cliffs"][name])


func _cliff_sprite(node: Node2D, name: String, left: int, top: int) -> void:
	var sprite: Sprite2D = _add(node, Sprite2D.new(), "%s_%d_%d" % [name.to_pascal_case(), left, top])
	sprite.texture = load("%s/%s.png" % [cfg["cliff_dir"], name])
	sprite.centered = false
	sprite.position = Vector2(left, top)


func _add_bridge(decor: Node2D, x0: int, y: int) -> void:
	var x1: int = x0
	while _ch(x1 + 1, y) == "=" and x1 + 1 < width:
		x1 += 1
	var tex: Texture2D = load("%s/bridge_h.png" % PROPS_TEX_DIR)
	var sprite: Sprite2D = _add(decor, Sprite2D.new(), "Bridge%d_%d" % [x0, y])
	sprite.texture = tex
	var target_w: float = (x1 - x0 + 3) * T
	var s: float = target_w / tex.get_width()
	sprite.scale = Vector2(s, s)
	sprite.position = Vector2((x0 + x1 + 1) * T / 2.0, y * T + T / 2.0)


func _add_prop(root: Node2D, entities: Node2D, scenes: Dictionary, name: String, x: int, y: int, foot: int) -> void:
	var inst: Node2D = (scenes[name] as PackedScene).instantiate()
	inst.name = "%s_%d_%d" % [name.to_pascal_case(), x, y]
	inst.position = Vector2(x * T + T / 2.0, (y + 1) * T - foot)
	entities.add_child(inst)
	inst.owner = root


func _tile_layer(parent: Node, tileset: TileSet, layer_name: String, offset: Vector2) -> TileMapLayer:
	var layer: TileMapLayer = _add(parent, TileMapLayer.new(), layer_name)
	layer.tile_set = tileset
	layer.position = offset
	return layer


func _add(parent: Node, node: Node, node_name: String) -> Node:
	node.name = node_name
	parent.add_child(node)
	return node
