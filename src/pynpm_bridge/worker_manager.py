"""WorkerManager - manages the Node.js worker process lifecycle."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import uuid as _uuid
from pathlib import Path
from typing import Any, Optional

from pynpm_bridge.exceptions import (
    WorkerCrashedError,
    WorkerTimeoutError,
    JavaScriptError,
    PynpmBridgeError,
)


class WorkerManager:
    """
    Manages the persistent Node.js worker process.

    Newline-delimited JSON-RPC over stdin/stdout.
    Requests matched by ID.
    """

    def __init__(
        self,
        workspace: Path,
        node_path: str = "node",
        default_timeout: float = 30.0,
    ):
        self._workspace = workspace
        self._node_path = node_path
        self._default_timeout = default_timeout
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._pending: dict[str, threading.Event] = {}
        self._results: dict[str, Any] = {}
        self._reader_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._running = False
        # incremented every time a worker process is started
        self._generation = 0

    def _find_worker_script(self) -> Path:
        target = self._workspace / "node_worker" / "worker.mjs"
        if target.is_file():
            return target.resolve()
        raise FileNotFoundError(f"Cannot find worker.mjs at {target}")

    def _is_alive(self) -> bool:
        return (
            self._process is not None and self._process.poll() is None and self._running
        )

    def ensure_running(self) -> None:
        with self._lock:
            if self._is_alive():
                return
            self._start_worker()

    def _start_worker(self) -> None:
        worker_script = self._find_worker_script()
        env = os.environ.copy()
        env["NODE_PATH"] = str(self._workspace / "node_modules")

        self._process = subprocess.Popen(
            [self._node_path, str(worker_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self._workspace),
            env=env,
        )
        # bump generation so proxies can tell whether they belong to the
        # current worker instance.  This is used to avoid accidentally
        # releasing handles from a previous process after a restart.
        self._generation += 1
        self._running = True
        self._pending.clear()
        self._results.clear()

        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="pynpm-reader"
        )
        self._reader_thread.start()

        self._stderr_thread = threading.Thread(
            target=self._stderr_reader_loop, daemon=True, name="pynpm-stderr"
        )
        self._stderr_thread.start()

        ready_event = threading.Event()
        self._pending["__ready__"] = ready_event
        if not ready_event.wait(timeout=15.0):
            self._kill_worker()
            raise PynpmBridgeError("Node.js worker failed to start within 15 seconds")
        self._results.pop("__ready__", None)
        self._pending.pop("__ready__", None)

    def _reader_loop(self) -> None:
        proc = self._process
        if proc is None or proc.stdout is None:
            return
        try:
            while self._running:
                raw = proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                mid = msg.get("id")
                if mid is None and msg.get("type") == "ready":
                    self._results["__ready__"] = True
                    evt = self._pending.get("__ready__")
                    if evt:
                        evt.set()
                    continue
                if mid is not None:
                    self._results[mid] = msg
                    evt = self._pending.get(mid)
                    if evt:
                        evt.set()
        except Exception:
            pass
        finally:
            self._running = False
            for evt in list(self._pending.values()):
                evt.set()

    def _stderr_reader_loop(self) -> None:
        proc = self._process
        if proc is None or proc.stderr is None:
            return
        try:
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
        except Exception:
            pass

    def _write_message(self, data: dict) -> None:
        proc = self._process
        if proc is None or proc.stdin is None or proc.poll() is not None:
            raise WorkerCrashedError()
        msg_bytes = (json.dumps(data) + "\n").encode("utf-8")
        with self._send_lock:
            try:
                proc.stdin.write(msg_bytes)
                proc.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise WorkerCrashedError() from exc

    def send_request(
        self,
        method: str,
        params: dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Any:
        self.ensure_running()
        request_id = str(_uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        event = threading.Event()
        self._pending[request_id] = event
        eff_timeout = timeout if timeout is not None else self._default_timeout
        try:
            self._write_message(request)
        except WorkerCrashedError:
            self._pending.pop(request_id, None)
            raise
        if not event.wait(timeout=eff_timeout):
            self._pending.pop(request_id, None)
            self._results.pop(request_id, None)
            raise WorkerTimeoutError(eff_timeout)
        self._pending.pop(request_id, None)
        result = self._results.pop(request_id, None)
        if result is None:
            raise WorkerCrashedError()
        if "error" in result:
            err = result["error"]
            raise JavaScriptError(
                message=err.get("message", "Unknown error"),
                js_stack=err.get("stack", ""),
                error_type=err.get("errorType", "Error"),
            )
        return result.get("result")

    def send_batch(
        self,
        requests: list[tuple[str, dict[str, Any]]],
        timeout: Optional[float] = None,
    ) -> list[Any]:
        self.ensure_running()
        eff_timeout = timeout if timeout is not None else self._default_timeout
        ids: list[str] = []
        events: list[threading.Event] = []
        for method, params in requests:
            rid = str(_uuid.uuid4())
            ids.append(rid)
            evt = threading.Event()
            self._pending[rid] = evt
            events.append(evt)
            self._write_message(
                {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
            )
        results = []
        for rid, evt in zip(ids, events):
            if not evt.wait(timeout=eff_timeout):
                raise WorkerTimeoutError(eff_timeout)
            self._pending.pop(rid, None)
            result = self._results.pop(rid, None)
            if result is None:
                raise WorkerCrashedError()
            if "error" in result:
                err = result["error"]
                raise JavaScriptError(
                    message=err.get("message", "Unknown error"),
                    js_stack=err.get("stack", ""),
                    error_type=err.get("errorType", "Error"),
                )
            results.append(result.get("result"))
        return results

    def _kill_worker(self) -> None:
        self._running = False
        proc = self._process
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
            self._process = None
        for evt in list(self._pending.values()):
            evt.set()

    def shutdown(self) -> None:
        self._running = False
        proc = self._process
        if proc is not None and proc.poll() is None:
            try:
                msg = (
                    json.dumps({"jsonrpc": "2.0", "method": "shutdown", "params": {}})
                    + "\n"
                )
                if proc.stdin:
                    proc.stdin.write(msg.encode("utf-8"))
                    proc.stdin.flush()
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._kill_worker()
                return
            self._process = None
        for evt in list(self._pending.values()):
            evt.set()
        self._pending.clear()
        self._results.clear()

    @property
    def is_running(self) -> bool:
        return self._is_alive()

    @property
    def generation(self) -> int:
        """A monotonically increasing counter incremented every time the
        worker process starts.  Consumers (e.g. :class:`JsProxy`) can compare
        their birth generation against this to determine whether they were
        created before a restart."""
        return self._generation
