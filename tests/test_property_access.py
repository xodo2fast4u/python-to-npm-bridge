from pynpm_bridge.proxy import JsProxy


def test_get_lodash_version(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    version = _.VERSION
    assert isinstance(version, str)
    assert version.startswith("4.")


def test_nested_property_access(runtime_with_packages):
    # Pure data objects serialize as dicts
    obj = runtime_with_packages.eval_js("({ a: { b: { c: 42 } } })")
    assert obj["a"]["b"]["c"] == 42


def test_nested_property_access_via_proxy(runtime_with_packages):
    # Use eval to create an object with a method so it becomes a JsProxy
    obj = runtime_with_packages.eval_js(
        "var _o = { a: { b: { c: 42 } }, get: function(k) { return this[k]; } }; _o"
    )
    assert isinstance(obj, JsProxy)
    # Access nested via proxy
    a = obj.a
    assert a["b"]["c"] == 42


def test_array_property_access(runtime_with_packages):
    arr = runtime_with_packages.eval_js("[10, 20, 30]")
    assert arr[0] == 10
    assert arr[1] == 20
    assert arr[2] == 30


def test_set_property_on_proxy(runtime_with_packages):
    # Create object with a method so it's returned as JsProxy
    obj = runtime_with_packages.eval_js("({ x: 1, inc: function() { this.x++; } })")
    assert isinstance(obj, JsProxy)
    obj.x = 42
    assert obj.x == 42


def test_set_new_property_on_proxy(runtime_with_packages):
    obj = runtime_with_packages.eval_js("({ dummy: function(){} })")
    assert isinstance(obj, JsProxy)
    obj.name = "test"
    assert obj.name == "test"


def test_property_is_function_returns_proxy(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    camel = _.camelCase
    assert isinstance(camel, JsProxy)
    assert camel("hello world") == "helloWorld"


def test_to_python_dict(runtime_with_packages):
    # Create an object with a method so it's a JsProxy, then to_python() it
    obj = runtime_with_packages.eval_js(
        '({ name: "Alice", age: 30, hobbies: ["reading", "coding"], greet: function() { return "hi"; } })'
    )
    assert isinstance(obj, JsProxy)
    data = obj.to_python()
    assert data["name"] == "Alice"
    assert data["age"] == 30
    assert data["hobbies"] == ["reading", "coding"]


def test_pure_data_object_is_dict(runtime_with_packages):
    """Pure data objects (no functions) are returned as Python dicts."""
    obj = runtime_with_packages.eval_js('({ name: "Alice", age: 30 })')
    assert isinstance(obj, dict)
    assert obj["name"] == "Alice"
    assert obj["age"] == 30
