extends Node2D
## Bootstrap do jogo: liga a câmera à região carregada em `World`.
## Fica fora de scripts/core porque depende de world (regra de dependência §9.3).

## Velocidade do pan de depuração em px/s (temporário até o treinador do M1).
const DEBUG_PAN_SPEED: float = 260.0

@onready var _camera: CameraRig = $CameraRig
@onready var _world: Node2D = $World

var _pan_target: Node2D


func _ready() -> void:
	var regions: Array[Region] = _find_regions()
	if regions.is_empty():
		return
	# Regiões vizinhas formam um mapa contínuo: a câmera fica presa à união delas.
	var all_bounds: Rect2i = regions[0].get_world_bounds()
	for r: Region in regions:
		all_bounds = all_bounds.merge(r.get_world_bounds())
	_camera.set_bounds(all_bounds)
	var region: Region = regions[0]
	# Sem treinador ainda: a câmera segue um marcador movido com WASD.
	_pan_target = Node2D.new()
	_pan_target.name = "DebugPanTarget"
	_pan_target.position = region.get_spawn_position()
	add_child(_pan_target)
	_camera.set_target(_pan_target)


func _physics_process(delta: float) -> void:
	if _pan_target == null:
		return
	var dir: Vector2 = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	_pan_target.position += dir * DEBUG_PAN_SPEED * delta


## Regiões filhas de `World`; a primeira dá o ponto de partida.
func _find_regions() -> Array[Region]:
	var found: Array[Region] = []
	for child: Node in _world.get_children():
		if child is Region:
			found.append(child)
	return found
