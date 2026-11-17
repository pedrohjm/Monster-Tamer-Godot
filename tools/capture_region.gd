extends SceneTree
## Renderiza uma região inteira (ou o World da main.tscn, com todas as regiões) em 1:1 e
## salva em PNG (precisa de janela, sem --headless).
##   Godot --path . -s res://tools/capture_region.gd -- <cena.tscn> <saida.png> [colisao]
## Com o terceiro argumento "colisao", a camada de colisão aparece em vermelho.

var _viewport: SubViewport
var _out: String
var _frames: int = 0


func _initialize() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var scene_path: String = args[0] if args.size() > 0 else "res://scenes/world/region_jungle_00.tscn"
	_out = args[1] if args.size() > 1 else "user://region_capture.png"
	var region: Node2D = (load(scene_path) as PackedScene).instantiate()
	# Cena com várias regiões (ex.: main.tscn): usa só o nó World (sem câmera e scripts
	# do jogo) e captura a união dos limites das regiões.
	var world: Node2D = region.get_node_or_null("World") as Node2D
	if world != null:
		region.remove_child(world)
		region.free()
		region = world
	var regions: Array[Node] = []
	if region.get("bounds") != null:
		regions.append(region)
	else:
		regions = region.find_children("*", "Region", true, false)
	var bounds: Rect2i = Rect2i()
	for r: Node2D in regions:
		var rb: Rect2i = r.get("bounds")
		rb.position += Vector2i(r.position.round())
		bounds = rb if bounds.size == Vector2i.ZERO else bounds.merge(rb)
		if args.size() > 2 and args[2] == "colisao":
			(r.get_node("Collision") as CanvasItem).visible = true
	region.position -= Vector2(bounds.position)
	_viewport = SubViewport.new()
	_viewport.size = bounds.size
	_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_viewport.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	_viewport.add_child(region)
	root.add_child(_viewport)


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames < 4:
		return false
	var img: Image = _viewport.get_texture().get_image()
	var err: Error = img.save_png(_out)
	print("captura salva em %s, erro=%d" % [_out, err])
	return true
