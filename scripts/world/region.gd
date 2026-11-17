class_name Region
extends Node2D
## Raiz de uma região do mundo (gerada por tools/build_region.gd).
## Expõe os limites do mapa para a câmera e o ponto de partida.

## Limites do mapa em pixels de mundo.
@export var bounds: Rect2i


## Limites do mapa em pixels globais (considera a posição da região no mundo).
func get_world_bounds() -> Rect2i:
	return Rect2i(bounds.position + Vector2i(global_position.round()), bounds.size)


## Posição global do nó `Spawn`, ou a origem da região se ele não existir.
func get_spawn_position() -> Vector2:
	var spawn: Node2D = get_node_or_null("Spawn") as Node2D
	return spawn.global_position if spawn != null else global_position


## Nó y-sorted onde ficam props, treinador e criaturas.
func get_entities() -> Node2D:
	return get_node("Entities") as Node2D
