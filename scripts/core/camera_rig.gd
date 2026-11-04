class_name CameraRig
extends Camera2D
## Câmera do jogo (substitui o Cinemachine do design original).
## Segue um alvo e troca de alvo com transição suave. Os limites do mapa
## (confiner) usam os `limit_*` da própria Camera2D.

## Nó seguido. Pode ficar vazio; a câmera fica parada.
@export var target: Node2D
## Velocidade do acompanhamento contínuo (maior = mais grudado no alvo).
@export var follow_speed: float = 10.0

var _blend_from: Vector2 = Vector2.ZERO
var _blend_time: float = 0.0
var _blend_elapsed: float = 0.0


func _ready() -> void:
	if target != null:
		global_position = target.global_position


func _physics_process(delta: float) -> void:
	if target == null:
		return
	var goal: Vector2 = target.global_position
	if _blend_elapsed < _blend_time:
		_blend_elapsed += delta
		var t: float = clampf(_blend_elapsed / _blend_time, 0.0, 1.0)
		global_position = _blend_from.lerp(goal, ease(t, -2.0))
	else:
		global_position = global_position.lerp(goal, 1.0 - exp(-follow_speed * delta))


## Troca o alvo. Com `blend_time` > 0 faz uma transição suave até o novo alvo.
func set_target(new_target: Node2D, blend_time: float = 0.0) -> void:
	target = new_target
	_blend_from = global_position
	_blend_time = maxf(blend_time, 0.0)
	_blend_elapsed = 0.0
	if new_target != null and _blend_time == 0.0:
		global_position = new_target.global_position
		reset_smoothing()


## Define os limites do mapa em pixels de mundo.
func set_bounds(bounds: Rect2i) -> void:
	limit_left = bounds.position.x
	limit_top = bounds.position.y
	limit_right = bounds.end.x
	limit_bottom = bounds.end.y
