"""Data marshaling between Python and JavaScript."""

from __future__ import annotations

import base64
import datetime
import math
from typing import Any

MAX_SAFE_INTEGER = 2**53 - 1
MIN_SAFE_INTEGER = -(2**53 - 1)


def python_to_js(value: Any) -> Any:
    """Convert a Python value to a JSON-safe representation for Node.js."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if MIN_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            return value
        return {"__type__": "bigint", "value": str(value)}
    if isinstance(value, float):
        if math.isnan(value):
            return {"__type__": "float_special", "value": "NaN"}
        if math.isinf(value):
            return {
                "__type__": "float_special",
                "value": "Infinity" if value > 0 else "-Infinity",
            }
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return {"__type__": "bytes", "data": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return {"__type__": "date", "iso": value.isoformat()}
    if isinstance(value, datetime.date):
        return {"__type__": "date", "iso": value.isoformat()}
    if isinstance(value, (list, tuple)):
        return [python_to_js(item) for item in value]
    if isinstance(value, dict):
        return {str(k): python_to_js(v) for k, v in value.items()}
    # JsProxy objects
    hid = getattr(value, "_handle_id", None)
    rt = getattr(value, "_runtime", None)
    if hid is not None and rt is not None:
        return {"__type__": "handle_ref", "handleId": hid}
    return str(value)


def js_to_python(value: Any, runtime: Any = None) -> Any:
    """Convert a JSON value from Node.js back to Python."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return [js_to_python(item, runtime) for item in value]
    if isinstance(value, dict):
        tag = value.get("__type__")
        if tag == "bigint":
            return int(value["value"])
        if tag == "bytes":
            return base64.b64decode(value["data"])
        if tag == "date":
            iso = value["iso"]
            try:
                return datetime.datetime.fromisoformat(iso)
            except ValueError:
                return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if tag == "undefined":
            return None
        if tag == "float_special":
            s = value["value"]
            if s == "NaN":
                return float("nan")
            if s == "Infinity":
                return float("inf")
            if s == "-Infinity":
                return float("-inf")
            return float("nan")
        if tag == "handle":
            if runtime is not None:
                from pynpm_bridge.proxy import JsProxy

                # attach the current worker generation so the proxy can
                # determine whether it was created before a restart.  This
                # prevents old proxies from accidentally releasing handles on
                # a newly started worker that may reuse the same id.
                gen = getattr(runtime._worker, "generation", 0)
                return JsProxy(
                    runtime=runtime,
                    handle_id=value["handleId"],
                    js_type=value.get("jsType", "object"),
                    preview=value.get("preview", ""),
                    props=value.get("props"),
                    generation=gen,
                )
            return value
        if tag == "error":
            from pynpm_bridge.exceptions import JavaScriptError

            raise JavaScriptError(
                message=value.get("message", "Unknown JS error"),
                js_stack=value.get("stack", ""),
                error_type=value.get("errorType", "Error"),
            )
        return {k: js_to_python(v, runtime) for k, v in value.items()}
    return value
