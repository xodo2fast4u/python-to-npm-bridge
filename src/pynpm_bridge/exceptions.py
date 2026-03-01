"""Exception types for pynpm_bridge."""


class PynpmBridgeError(Exception):
    """Base exception for all pynpm_bridge errors."""

    pass


class JavaScriptError(PynpmBridgeError):
    """
    Raised when JavaScript code throws an exception.

    Attributes:
        message: The error message from JavaScript.
        js_stack: The JavaScript stack trace string.
        error_type: The JS error constructor name (e.g., 'TypeError').
    """

    def __init__(self, message: str, js_stack: str = "", error_type: str = "Error"):
        self.message = message
        self.js_stack = js_stack
        self.error_type = error_type
        full_msg = f"{error_type}: {message}"
        if js_stack:
            full_msg += f"\n\nJavaScript Stack Trace:\n{js_stack}"
        super().__init__(full_msg)


class WorkerCrashedError(PynpmBridgeError):
    """Raised when the Node.js worker process has crashed."""

    def __init__(self, message: str = "Node.js worker process crashed"):
        super().__init__(message)


class WorkerTimeoutError(PynpmBridgeError):
    """Raised when a call to the Node.js worker times out."""

    def __init__(self, timeout: float):
        super().__init__(f"Call to Node.js worker timed out after {timeout}s")
        self.timeout = timeout


class PackageNotAllowedError(PynpmBridgeError):
    """Raised when attempting to install a package not in the allowlist."""

    def __init__(self, package_name: str):
        super().__init__(
            f"Package '{package_name}' is not in the allowed packages list"
        )
        self.package_name = package_name
