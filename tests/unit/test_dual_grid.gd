extends "res://tests/test_case.gd"


func test_full_and_empty_masks() -> void:
	assert_eq(DualGrid.atlas_coords(DualGrid.mask(true, true, true, true)), Vector2i(2, 1))
	assert_eq(DualGrid.atlas_coords(DualGrid.mask(false, false, false, false)), Vector2i(0, 3))


func test_single_corners() -> void:
	assert_eq(DualGrid.atlas_coords(DualGrid.mask(true, false, false, false)), Vector2i(3, 3))
	assert_eq(DualGrid.atlas_coords(DualGrid.mask(false, true, false, false)), Vector2i(0, 2))
	assert_eq(DualGrid.atlas_coords(DualGrid.mask(false, false, true, false)), Vector2i(0, 0))
	assert_eq(DualGrid.atlas_coords(DualGrid.mask(false, false, false, true)), Vector2i(1, 3))


func test_every_atlas_cell_used_once() -> void:
	var seen: Dictionary = {}
	for m: int in 16:
		seen[DualGrid.atlas_coords(m)] = true
	assert_eq(seen.size(), 16)


func test_corner_and_display_cells_are_inverse() -> void:
	var cell: Vector2i = Vector2i(5, -3)
	for d: Vector2i in DualGrid.display_cells(cell):
		assert_true(DualGrid.corner_cells(d).has(cell), "tile visual %s deveria usar a célula %s" % [d, cell])


func test_variant_pick_is_stable() -> void:
	var w: PackedFloat32Array = PackedFloat32Array([0.05, 0.05])
	assert_eq(DualGrid.pick_variant(Vector2i(10, 4), w), DualGrid.pick_variant(Vector2i(10, 4), w))


func test_variant_rate_matches_weights() -> void:
	var w: PackedFloat32Array = PackedFloat32Array([0.05, 0.05, 0.03])
	var picked: int = 0
	for y: int in 100:
		for x: int in 100:
			if DualGrid.pick_variant(Vector2i(x, y), w) >= 0:
				picked += 1
	assert_almost_eq(picked / 10000.0, 0.13, 0.02)


func test_no_weights_always_base() -> void:
	assert_eq(DualGrid.pick_variant(Vector2i(3, 3), PackedFloat32Array()), -1)
