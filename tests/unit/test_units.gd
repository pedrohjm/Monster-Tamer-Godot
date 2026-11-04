extends "res://tests/test_case.gd"


func test_tile_is_32_pixels() -> void:
	assert_eq(Units.TILE, 32)


func test_leash_of_10_tiles_is_320_pixels() -> void:
	assert_almost_eq(Units.tiles(10), 320.0)


func test_pixels_back_to_tiles() -> void:
	assert_almost_eq(Units.to_tiles(48.0), 1.5)
