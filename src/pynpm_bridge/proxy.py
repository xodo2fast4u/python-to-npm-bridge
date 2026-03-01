"""JsProxy - Python proxy for a JavaScript object in the Node worker."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pynpm_bridge.runtime import NpmRuntime


class JsProxy:
    """
    Python proxy for a JavaScript object living in the Node.js worker.

    Attribute access, function calls, constructor invocation,
    iteration, and explicit disposal are all supported.
    """

    __slots__ = (
        "_runtime",
        "_handle_id",
        "_js_type",
        "_preview",
        "_props",
        "_disposed",
        "_generation",
    )

    def __init__(
        self,
        runtime: NpmRuntime,
        handle_id: str,
        js_type: str = "object",
        preview: str = "",
        props: Optional[list[str]] = None,
        generation: int = 0,
    ):
        object.__setattr__(self, "_runtime", runtime)
        object.__setattr__(self, "_handle_id", handle_id)
        object.__setattr__(self, "_js_type", js_type)
        object.__setattr__(self, "_preview", preview)
        object.__setattr__(self, "_props", props)
        object.__setattr__(self, "_disposed", False)
        object.__setattr__(self, "_generation", generation)

    def __repr__(self) -> str:
        hid = object.__getattribute__(self, "_handle_id")
        if object.__getattribute__(self, "_disposed"):
            return f"<JsProxy [disposed] handle={hid}>"
        jt = object.__getattribute__(self, "_js_type")
        pv = object.__getattribute__(self, "_preview")
        ps = f" {pv}" if pv else ""
        return f"<JsProxy({jt}){ps} handle={hid}>"

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        rt = object.__getattribute__(self, "_runtime")
        hid = object.__getattribute__(self, "_handle_id")
        return rt._get_property(hid, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        rt = object.__getattribute__(self, "_runtime")
        hid = object.__getattribute__(self, "_handle_id")
        rt._set_property(hid, name, value)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        rt = object.__getattribute__(self, "_runtime")
        hid = object.__getattribute__(self, "_handle_id")
        return rt._call_function(hid, list(args))

    def new(self, *args: Any) -> Any:
        """Invoke as constructor: equivalent to ``new Obj(args...)`` in JS."""
        rt = object.__getattribute__(self, "_runtime")
        hid = object.__getattribute__(self, "_handle_id")
        return rt._construct(hid, list(args))

    def to_python(self) -> Any:
        """Force full serialization of the JS object to a Python dict/list."""
        rt = object.__getattribute__(self, "_runtime")
        hid = object.__getattribute__(self, "_handle_id")
        return rt._to_python(hid)

    def dispose(self) -> None:
        """Release the JS-side handle.

        Handles are only released against the worker process which created
        them.  After a restart the generation number on the runtime will
        differ, and releasing against the new process could inadvertently
        free a handle that happens to reuse the same id.  Skip the release
        in that case.
        """
        if not object.__getattribute__(self, "_disposed"):
            object.__setattr__(self, "_disposed", True)
            try:
                rt = object.__getattribute__(self, "_runtime")
                hid = object.__getattribute__(self, "_handle_id")
                gen = object.__getattribute__(self, "_generation")
                if getattr(rt._worker, "generation", None) == gen:
                    rt._release_handle(hid)
            except Exception:
                pass

    def __del__(self) -> None:
        try:
            if not object.__getattribute__(self, "_disposed"):
                object.__setattr__(self, "_disposed", True)
                rt = object.__getattribute__(self, "_runtime")
                hid = object.__getattribute__(self, "_handle_id")
                gen = object.__getattribute__(self, "_generation")
                if not rt._closed and getattr(rt._worker, "generation", None) == gen:
                    rt._release_handle(hid)
        except Exception:
            pass

    def __len__(self) -> int:
        rt = object.__getattribute__(self, "_runtime")
        hid = object.__getattribute__(self, "_handle_id")
        length = rt._get_property(hid, "length")
        if isinstance(length, JsProxy):
            val = length.to_python()
            length.dispose()
            return int(val)
        return int(length)

    def __getitem__(self, key: Any) -> Any:
        rt = object.__getattribute__(self, "_runtime")
        hid = object.__getattribute__(self, "_handle_id")
        return rt._get_property(hid, key)

    def __setitem__(self, key: Any, value: Any) -> None:
        rt = object.__getattribute__(self, "_runtime")
        hid = object.__getattribute__(self, "_handle_id")
        rt._set_property(hid, str(key), value)

    def __iter__(self):
        try:
            n = len(self)
        except Exception:
            raise TypeError("JS object is not iterable (no .length property)")
        for i in range(n):
            yield self[i]

    def __bool__(self) -> bool:
        return True

    def __str__(self) -> str:
        try:
            rt = object.__getattribute__(self, "_runtime")
            hid = object.__getattribute__(self, "_handle_id")
            result = rt._call_method(hid, "toString", [])
            if isinstance(result, JsProxy):
                val = result.to_python()
                result.dispose()
                return str(val)
            return str(result)
        except Exception:
            return repr(self)
