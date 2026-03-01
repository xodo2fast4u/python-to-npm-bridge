import datetime
import math


def test_string_roundtrip(runtime_with_packages):
    assert runtime_with_packages.eval_js("'hello world'") == "hello world"


def test_number_roundtrip(runtime_with_packages):
    assert runtime_with_packages.eval_js("42") == 42


def test_float_roundtrip(runtime_with_packages):
    assert abs(runtime_with_packages.eval_js("3.14159") - 3.14159) < 1e-10


def test_boolean_roundtrip(runtime_with_packages):
    assert runtime_with_packages.eval_js("true") is True
    assert runtime_with_packages.eval_js("false") is False


def test_null_roundtrip(runtime_with_packages):
    assert runtime_with_packages.eval_js("null") is None


def test_undefined_roundtrip(runtime_with_packages):
    assert runtime_with_packages.eval_js("undefined") is None


def test_array_roundtrip(runtime_with_packages):
    assert runtime_with_packages.eval_js("[1, 2, 3]") == [1, 2, 3]


def test_object_roundtrip(runtime_with_packages):
    r = runtime_with_packages.eval_js('({ a: 1, b: "two", c: true })')
    assert r == {"a": 1, "b": "two", "c": True}


def test_nested_structure(runtime_with_packages):
    r = runtime_with_packages.eval_js(
        '({ users: [{ name: "Alice", age: 30 }, { name: "Bob", age: 25 }] })'
    )
    assert r["users"][0]["name"] == "Alice"
    assert r["users"][1]["age"] == 25


def test_bytes_roundtrip(runtime_with_packages):
    assert (
        runtime_with_packages.eval_js("Buffer.from('aGVsbG8gd29ybGQ=', 'base64')")
        == b"hello world"
    )


def test_nan_handling(runtime_with_packages):
    assert math.isnan(runtime_with_packages.eval_js("NaN"))


def test_infinity_handling(runtime_with_packages):
    r = runtime_with_packages.eval_js("Infinity")
    assert math.isinf(r) and r > 0
    r2 = runtime_with_packages.eval_js("-Infinity")
    assert math.isinf(r2) and r2 < 0


def test_date_from_js(runtime_with_packages):
    r = runtime_with_packages.eval_js("new Date('2025-06-15T12:00:00Z')")
    assert isinstance(r, datetime.datetime)
    assert r.year == 2025 and r.month == 6 and r.day == 15


def test_passing_list_to_function(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.sum([1, 2, 3, 4, 5]) == 15


def test_passing_dict_to_function(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.get({"a": {"b": 42}}, "a.b") == 42


def test_large_integer_serialization():
    from pynpm_bridge.serializer import python_to_js

    big = 2**53 + 1
    assert python_to_js(big) == {"__type__": "bigint", "value": str(big)}
