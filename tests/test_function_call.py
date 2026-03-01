def test_lodash_camelcase(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.camelCase("hello world") == "helloWorld"
    assert _.camelCase("foo-bar") == "fooBar"
    assert _.camelCase("__FOO_BAR__") == "fooBar"


def test_lodash_chunk(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_lodash_uniq(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.uniq([1, 1, 2, 3, 3, 4]) == [1, 2, 3, 4]


def test_lodash_flatten(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.flatten([1, [2, [3, [4]], 5]]) == [1, 2, [3, [4]], 5]


def test_lodash_is_functions(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.isString("hello") is True
    assert _.isString(42) is False
    assert _.isNumber(42) is True
    assert _.isArray([1, 2]) is True


def test_function_with_no_args(runtime_with_packages):
    uuid_mod = runtime_with_packages.require("uuid")
    assert isinstance(uuid_mod.v4(), str)


def test_function_with_dict_arg(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert sorted(_.keys({"a": 1, "b": 2, "c": 3})) == ["a", "b", "c"]


def test_function_with_none_arg(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.isNull(None) is True


def test_lodash_sum(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.sum([1, 2, 3, 4, 5]) == 15
