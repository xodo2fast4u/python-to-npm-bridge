import pytest
from pynpm_bridge.runtime import NpmRuntime
from pynpm_bridge.exceptions import PackageNotAllowedError


def test_install_lodash(runtime_with_packages):
    _ = runtime_with_packages.require("lodash")
    assert _.isString("hello") is True


def test_install_exact_version(runtime):
    runtime.install("lodash", "4.17.21")
    _ = runtime.require("lodash")
    assert _.camelCase("test string") == "testString"


def test_install_semver_range(runtime):
    runtime.install("lodash", "^4.17.0")
    _ = runtime.require("lodash")
    assert _.isArray([1, 2, 3]) is True


def test_install_latest(runtime):
    runtime.install("lodash")
    _ = runtime.require("lodash")
    assert _ is not None


def test_install_allowlist_pass():
    rt = NpmRuntime(allowed_packages={"lodash"}, timeout=60.0)
    try:
        rt.install("lodash", "^4.17.21")
        _ = rt.require("lodash")
        assert _.isNumber(42) is True
    finally:
        rt.close()


def test_install_allowlist_block():
    rt = NpmRuntime(allowed_packages={"lodash"}, timeout=60.0)
    try:
        with pytest.raises(PackageNotAllowedError):
            rt.install("express")
    finally:
        rt.close()
