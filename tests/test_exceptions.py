import pytest
from pynpm_bridge.exceptions import JavaScriptError
from pynpm_bridge.proxy import JsProxy


def test_js_error_is_raised(runtime_with_packages):
    with pytest.raises(JavaScriptError) as exc_info:
        runtime_with_packages.eval_js("throw new Error('test error')")
    assert "test error" in str(exc_info.value)


def test_js_error_has_message(runtime_with_packages):
    with pytest.raises(JavaScriptError) as exc_info:
        runtime_with_packages.eval_js("throw new Error('specific message')")
    assert exc_info.value.message == "specific message"


def test_js_error_has_type(runtime_with_packages):
    with pytest.raises(JavaScriptError) as exc_info:
        runtime_with_packages.eval_js("throw new TypeError('type problem')")
    assert exc_info.value.error_type == "TypeError"


def test_js_error_has_stack(runtime_with_packages):
    with pytest.raises(JavaScriptError) as exc_info:
        runtime_with_packages.eval_js("throw new Error('with stack')")
    assert exc_info.value.js_stack != ""


def test_js_reference_error(runtime_with_packages):
    with pytest.raises(JavaScriptError) as exc_info:
        runtime_with_packages.eval_js("undefinedVariable")
    assert exc_info.value.error_type == "ReferenceError"


def test_js_syntax_error(runtime_with_packages):
    with pytest.raises(JavaScriptError):
        runtime_with_packages.eval_js("function {{{")


def test_nonfunction_primitive_is_not_proxy(runtime_with_packages):
    obj = runtime_with_packages.eval_js("({ notAFunction: 42 })")
    # Pure data objects (no function properties) come back as dicts
    assert isinstance(obj, dict)
    assert obj["notAFunction"] == 42
