extends SceneTree
## Runner headless: godot --headless --path . -s res://tests/run_tests.gd
## Roda todo tests/unit/test_*.gd e sai com código 1 se algo falhar.

const UNIT_DIR: String = "res://tests/unit"


func _initialize() -> void:
	var passed: int = 0
	var failed: int = 0
	for file_name: String in _test_files():
		var script: GDScript = load(UNIT_DIR.path_join(file_name)) as GDScript
		if script == null:
			print("ERRO  não carregou %s" % file_name)
			failed += 1
			continue
		for method: Dictionary in script.get_script_method_list():
			var method_name: String = method["name"]
			if not method_name.begins_with("test_"):
				continue
			var test_case: RefCounted = script.new()
			test_case.call(method_name)
			var failures: PackedStringArray = test_case.get("failures")
			if failures.is_empty():
				passed += 1
				print("ok    %s::%s" % [file_name, method_name])
			else:
				failed += 1
				print("FALHA %s::%s" % [file_name, method_name])
				for text: String in failures:
					print("      %s" % text)
	print("\n%d passaram, %d falharam" % [passed, failed])
	quit(1 if failed > 0 else 0)


func _test_files() -> PackedStringArray:
	var result: PackedStringArray = PackedStringArray()
	for file_name: String in DirAccess.get_files_at(UNIT_DIR):
		if file_name.begins_with("test_") and file_name.ends_with(".gd"):
			result.append(file_name)
	result.sort()
	return result
