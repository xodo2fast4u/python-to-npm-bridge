import pytest
from pynpm_bridge.exceptions import JavaScriptError
from pynpm_bridge.proxy import JsProxy


def test_require_lodash(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _ is not None
    assert _.camelCase("hello world") == "helloWorld"


def test_require_uuid(runtime_with_packages):
    uuid_mod = runtime_with_packages.require("uuid")
    v4 = uuid_mod.v4()
    assert isinstance(v4, str)
    assert len(v4) == 36


def test_require_returns_proxy(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert isinstance(_, JsProxy)


def test_require_nonexistent_package(runtime_with_packages):
    with pytest.raises(JavaScriptError):
        runtime_with_packages.require("nonexistent-package-xyz-12345")
