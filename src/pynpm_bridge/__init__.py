"""pynpm_bridge - Use npm packages from Python via a persistent Node.js runtime bridge."""

__version__ = "1.0.0"


def _check_import():
    """Verify all submodules load correctly."""
    pass


from pynpm_bridge.exceptions import (
    PynpmBridgeError,
    JavaScriptError,
    WorkerCrashedError,
    WorkerTimeoutError,
    PackageNotAllowedError,
)
from pynpm_bridge.proxy import JsProxy
from pynpm_bridge.runtime import NpmRuntime

__all__ = [
    "NpmRuntime",
    "JsProxy",
    "JavaScriptError",
    "WorkerCrashedError",
    "WorkerTimeoutError",
    "PackageNotAllowedError",
    "PynpmBridgeError",
    "__version__",
]
