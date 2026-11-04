extends RefCounted
## Base dos testes de lógica pura. Cada arquivo em tests/unit/test_*.gd estende
## este script; o runner chama todo método que começa com `test_`.

var failures: PackedStringArray = PackedStringArray()


func assert_true(condition: bool, message: String = "") -> void:
	if not condition:
		_fail("esperava true. %s" % message)


func assert_eq(actual: Variant, expected: Variant, message: String = "") -> void:
	if typeof(actual) != typeof(expected) or actual != expected:
		_fail("esperava %s, veio %s. %s" % [var_to_str(expected), var_to_str(actual), message])


func assert_almost_eq(actual: float, expected: float, tolerance: float = 0.0001, message: String = "") -> void:
	if absf(actual - expected) > tolerance:
		_fail("esperava %f (±%f), veio %f. %s" % [expected, tolerance, actual, message])


func _fail(text: String) -> void:
	failures.append(text)
