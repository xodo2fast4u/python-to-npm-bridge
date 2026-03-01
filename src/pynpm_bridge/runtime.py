"""NpmRuntime - main user-facing API for pynpm_bridge."""

from __future__ import annotations

import atexit
import json
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from pynpm_bridge.exceptions import (
    PackageNotAllowedError,
    PynpmBridgeError,
)
from pynpm_bridge.proxy import JsProxy
from pynpm_bridge.serializer import python_to_js, js_to_python
from pynpm_bridge.worker_manager import WorkerManager


def _find_worker_source() -> Path:
    """Locate the canonical worker.mjs shipped with pynpm_bridge."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "node_worker" / "worker.mjs",
        here.parent.parent / "node_worker" / "worker.mjs",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        "Cannot find worker.mjs. Searched:\n" + "\n".join(f"  {c}" for c in candidates)
    )


class NpmRuntime:
    """
    Main entry point for using npm packages from Python.

    Example::

        with NpmRuntime() as runtime:
            runtime.install("lodash", "^4.17.21")
            _ = runtime.require("lodash")
            print(_.camelCase("hello world"))
    """

    def __init__(
        self,
        workspace: Optional[str | Path] = None,
        node_path: str = "node",
        timeout: float = 30.0,
        allowed_packages: Optional[set[str]] = None,
    ):
        self._owns_workspace = workspace is None
        if workspace is None:
            self._workspace = Path(tempfile.mkdtemp(prefix="pynpm_"))
        else:
            self._workspace = Path(workspace).resolve()
            self._workspace.mkdir(parents=True, exist_ok=True)

        self._node_path = node_path
        self._timeout = timeout
        self._allowed_packages = allowed_packages
        self._closed = False

        self._init_package_json()
        self._deploy_worker()

        self._worker = WorkerManager(
            workspace=self._workspace,
            node_path=self._node_path,
            default_timeout=self._timeout,
        )
        atexit.register(self._atexit_close)

    def _atexit_close(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _init_package_json(self) -> None:
        pkg = self._workspace / "package.json"
        if not pkg.exists():
            pkg.write_text(
                json.dumps(
                    {
                        "name": "pynpm-workspace",
                        "version": "1.0.0",
                        "private": True,
                        "type": "commonjs",
                    },
                    indent=2,
                )
            )

    def _deploy_worker(self) -> None:
        dst_dir = self._workspace / "node_worker"
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "worker.mjs"
        src = _find_worker_source()
        # Always overwrite so code updates take effect
        shutil.copy2(str(src), str(dst))

    def __enter__(self) -> NpmRuntime:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._worker.shutdown()
        except Exception:
            pass
        if self._owns_workspace:
            shutil.rmtree(self._workspace, ignore_errors=True)

    def install(self, package: str, version: Optional[str] = None) -> str:
        if self._allowed_packages is not None and package not in self._allowed_packages:
            raise PackageNotAllowedError(package)
        spec = f"{package}@{version}" if version else package
        try:
            result = subprocess.run(
                ["npm", "install", "--save", spec],
                cwd=str(self._workspace),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise PynpmBridgeError(f"npm install {spec} failed:\n{result.stderr}")
        except FileNotFoundError:
            raise PynpmBridgeError("npm not found in PATH")
        except subprocess.TimeoutExpired:
            raise PynpmBridgeError(f"npm install {spec} timed out")
        return spec

    def require(self, module_name: str) -> Any:
        result = self._worker.send_request(
            "require", {"moduleName": module_name}, timeout=self._timeout
        )
        return js_to_python(result, runtime=self)

    def import_module(self, module_name: str) -> Any:
        result = self._worker.send_request(
            "import", {"moduleName": module_name}, timeout=self._timeout
        )
        return js_to_python(result, runtime=self)

    def eval_js(self, code: str) -> Any:
        result = self._worker.send_request(
            "eval", {"code": code}, timeout=self._timeout
        )
        return js_to_python(result, runtime=self)

    @contextmanager
    def batch(self):
        batcher = _BatchContext(self)
        yield batcher
        batcher._execute()

    def _get_property(self, handle_id: str, prop: Any) -> Any:
        result = self._worker.send_request(
            "getProperty",
            {"handleId": handle_id, "property": prop},
            timeout=self._timeout,
        )
        return js_to_python(result, runtime=self)

    def _set_property(self, handle_id: str, prop: str, value: Any) -> None:
        self._worker.send_request(
            "setProperty",
            {"handleId": handle_id, "property": prop, "value": python_to_js(value)},
            timeout=self._timeout,
        )

    def _call_function(self, handle_id: str, args: list) -> Any:
        result = self._worker.send_request(
            "call",
            {"handleId": handle_id, "args": [python_to_js(a) for a in args]},
            timeout=self._timeout,
        )
        return js_to_python(result, runtime=self)

    def _call_method(self, handle_id: str, method: str, args: list) -> Any:
        result = self._worker.send_request(
            "callMethod",
            {
                "handleId": handle_id,
                "method": method,
                "args": [python_to_js(a) for a in args],
            },
            timeout=self._timeout,
        )
        return js_to_python(result, runtime=self)

    def _construct(self, handle_id: str, args: list) -> Any:
        result = self._worker.send_request(
            "construct",
            {"handleId": handle_id, "args": [python_to_js(a) for a in args]},
            timeout=self._timeout,
        )
        return js_to_python(result, runtime=self)

    def _to_python(self, handle_id: str) -> Any:
        result = self._worker.send_request(
            "serialize", {"handleId": handle_id}, timeout=self._timeout
        )
        return js_to_python(result, runtime=self)

    def _release_handle(self, handle_id: str) -> None:
        if self._closed or not self._worker.is_running:
            return
        try:
            self._worker.send_request(
                "releaseHandle", {"handleId": handle_id}, timeout=5.0
            )
        except Exception:
            pass

    @staticmethod
    def init_workspace(path: str | Path) -> Path:
        ws = Path(path).resolve()
        ws.mkdir(parents=True, exist_ok=True)
        pkg = ws / "package.json"
        if not pkg.exists():
            pkg.write_text(
                json.dumps(
                    {
                        "name": "pynpm-workspace",
                        "version": "1.0.0",
                        "private": True,
                        "type": "commonjs",
                    },
                    indent=2,
                )
            )
        return ws


class _BatchContext:
    def __init__(self, runtime: NpmRuntime):
        self._runtime = runtime
        self._requests: list[tuple[str, dict[str, Any]]] = []
        self.results: list[Any] = []

    def call(self, handle_id: str, args: list) -> None:
        self._requests.append(
            ("call", {"handleId": handle_id, "args": [python_to_js(a) for a in args]})
        )

    def get(self, handle_id: str, prop: str) -> None:
        self._requests.append(
            ("getProperty", {"handleId": handle_id, "property": prop})
        )

    def require(self, module_name: str) -> None:
        self._requests.append(("require", {"moduleName": module_name}))

    def _execute(self) -> None:
        if not self._requests:
            return
        raw = self._runtime._worker.send_batch(self._requests)
        self.results = [js_to_python(r, runtime=self._runtime) for r in raw]
