from pynpm_bridge.proxy import JsProxy


def test_construct_date_via_eval(runtime_with_packages):
    DateCtor = runtime_with_packages.eval_js("Date")
    d = DateCtor.new("2025-06-15")
    assert isinstance(d, JsProxy)
    year = d.getFullYear()
    assert year == 2025


def test_construct_map_via_eval(runtime_with_packages):
    MapCtor = runtime_with_packages.eval_js("Map")
    m = MapCtor.new()
    m.set("key1", "value1")
    m.set("key2", "value2")
    assert m.size == 2
    assert m.get("key1") == "value1"


def test_construct_set_via_eval(runtime_with_packages):
    SetCtor = runtime_with_packages.eval_js("Set")
    s = SetCtor.new([1, 2, 3, 2, 1])
    assert s.size == 3
    assert s.has(2) is True
    assert s.has(5) is False


def test_class_instance_is_proxy(runtime_with_packages):
    DateCtor = runtime_with_packages.eval_js("Date")
    d = DateCtor.new()
    assert isinstance(d, JsProxy)


def test_method_chaining(runtime_with_packages):
    dayjs = runtime_with_packages.import_module("dayjs")
    assert dayjs("2025-03-15").add(1, "month").format("YYYY-MM-DD") == "2025-04-15"
