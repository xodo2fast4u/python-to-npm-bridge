![Logo](https://files.catbox.moe/dyg3je.webp)

Use npm packages directly from Python with JavaScript equivalent behavior.

## Why?

Python has great libraries for data science, ML and backend services. JavaScript has the npm ecosystem 275 million packages for everything from date handling to cryptography. What if you could just... use both?

`pynpm_bridge` lets you install and call any npm package from Python without switching languages, learning Node.js APIs, or spawning subprocess commands. It feels native. Errors come back as Python exceptions. JS objects behave like Python objects. You just use them.

## How It Works

Under the hood, `pynpm_bridge` spins up a persistent Node.js worker process in the background. Instead of spawning a new process for each call (slow) or saving files back and forth (messy), the worker stays alive and your Python code talks to it through a message-based protocol. Your Python code sends "call this function with these arguments", the worker executes it and sends back the result. If a JS function returns an object, Python gets a proxy—you don't copy the whole object, you hold a reference to it on the Node side.

## Installation

```bash
pip install -e ".[dev]"
```

You'll need:

- Python 3.10+
- Node.js 20+ (LTS) and npm — [install here](https://nodejs.org/en/download)

## 30-Second Example

```python
from pynpm_bridge import NpmRuntime

with NpmRuntime() as runtime:
    # Install a package
    runtime.install("lodash", "^4.17.21")

    # Load it—just like require() in JavaScript
    _ = runtime.require("lodash")

    # Call functions. Errors come back as Python exceptions.
    result = _.camelCase("hello world")
    print(result)  # "helloWorld"

    # ESM modules work too
    dayjs = runtime.import_module("date-fns")
    today = dayjs.format("2026-01-01", "yyyy-MM-dd")
    print(today)  # "2026-01-01"

# Runtime closes automatically (worker shuts down)
```

That's it. The `with` statement handles cleanup. If you need finer control, create a runtime and call `runtime.close()` when done.

## How Objects Work Across the Python-JavaScript Bridge

When a JavaScript function returns an object, you don't copy the whole thing to Python. Instead, you get a **proxy** a lightweight Python object that talks back to the Node.js worker:

```python
with NpmRuntime() as runtime:
    lodash = runtime.require("lodash")

    # lodash is a JsProxy pointing to the real JS object in Node
    # When you call lodash.camelCase(), it sends a message to Node,
    # Node runs it, and the result comes back
    result = lodash.camelCase("hello world")
```

Behind the scenes:

- Each object in JavaScript gets a unique ID (a "handle")
- Your Python proxy sends messages like: "Call function 123 with these args"
- Node runs it and sends back the result
- When Python garbage-collects your proxy, the handle is freed on the Node side
- This lets you work with large objects, complex state, and expensive resources without copying overhead

## CLI (optional)

```bash
# Initialize a Node.js workspace in a specific directory
pynpm init /path/to/project

# Install a package
pynpm install lodash@^4.17.21

# Run the demo
pynpm run-demo
```

## API Reference

### `NpmRuntime(workspace=None, node_path="node", timeout=30.0, allowed_packages=None)`

**Parameters:**

- `workspace`: Directory where npm packages are installed. If `None`, a temp directory is created and cleaned up when the runtime closes.
- `node_path`: Path to your Node.js binary (defaults to `"node"`, assumes it's in your `$PATH`)
- `timeout`: Default timeout in seconds for function calls (default: 30.0)
- `allowed_packages`: Optional set of package names to allowlist. If provided, only these packages can be installed. Useful if you're running untrusted code. See Security Model below.

**Methods:**

- `install(package, version=None)`: Install an npm package. `version` is optional (e.g., `"^4.17.21"`).
- `require(module_name)` → `JsProxy`: Load a CommonJS module
- `import_module(module_name)` → `JsProxy`: Load an ESM (ES6 module)
- `eval_js(code)` → result: Execute arbitrary JavaScript. Returns results as Python objects or JsProxy handles. **Use carefully—this runs untrusted code.**
- `close()`: Shut down the Node.js worker and clean up
- `batch()`: Context manager for batching calls. Useful for performance: sends multiple calls to Node in one message instead of one-by-one.

### `JsProxy`

A Python proxy to a JavaScript object. Returned from `require()`, `import_module()`, and any JS call that returns an object.

**Operations:**

- `proxy.foo`: Get a property (returns a Python value or another JsProxy if it's an object)
- `proxy(arg1, arg2)`: Call the object as a function
- `proxy.new(arg1, arg2)`: Construct with the `new` keyword
- `proxy.method_name(args)`: Call a method
- `for item in proxy:`: Iterate if the object is an array
- `proxy.to_python()`: Serialize the entire object to Python (dict/list). Useful if you want to move data entirely to Python instead of keeping a reference.
- `proxy.dispose()`: Free the reference manually. Normally happens automatically when the proxy is garbage-collected.

### `JavaScriptError`

Raised when JavaScript code throws an exception. Catch it to handle JS errors from Python:

```python
from pynpm_bridge import JavaScriptError

try:
    result = some_proxy.something_that_fails()
except JavaScriptError as e:
    print(f"JS Error: {e.message}")
    print(f"Type: {e.error_type}")  # e.g., "TypeError"
    print(f"Stack: {e.js_stack}")
```

**Attributes:**

- `message`: The error message from JavaScript
- `error_type`: The original JS error constructor name (e.g., `"TypeError"`, `"ReferenceError"`)
- `js_stack`: JavaScript stack trace

## Data Marshaling (Type Conversion)

When you pass Python values to JavaScript (or vice versa), they're automatically converted:

| Python     | JavaScript           | Notes                              |
| ---------- | -------------------- | ---------------------------------- |
| `None`     | `null`               | —                                  |
| `bool`     | `boolean`            | —                                  |
| `int`      | `number` or `BigInt` | Integers > 2⁵³ become BigInt in JS |
| `float`    | `number`             | —                                  |
| `str`      | `string`             | —                                  |
| `list`     | `Array`              | —                                  |
| `dict`     | `Object`             | —                                  |
| `bytes`    | `Buffer`             | Sent as base64                     |
| `datetime` | `Date`               | Sent as ISO 8601 string            |

**Big Numbers:** If your Python integer is larger than 2⁵³ - 1 (the largest safe integer in JavaScript), it's converted to a BigInt in the Node worker, and converted back to a Python `int` when it returns.

**Datetimes:** Python `datetime` objects are converted to ISO 8601 strings. When they come back from JavaScript as `Date` objects, they're converted back to Python `datetime`. Timezone-naive datetimes are assumed to be UTC.
deserialized back to Python datetime objects. Timezone-naive datetimes are treated as UTC.

## Security Model

**Be honest with yourself about what you're doing:** `pynpm_bridge` runs JavaScript code. That code runs in your Python process with your OS privileges.

**What this means:**

- npm packages execute arbitrary code in the Node.js worker
- That code can read/write files, make network requests, execute system commands, etc.
- Transitive dependencies are not sandboxed—if lodash depends on 50 other packages, all of them run too
- If you call `eval_js()` with untrusted input, it runs as-is

**When is this a problem?**

- If you're installing packages from untrusted sources (compromised npm registry, typosquatting, etc.)
- If you're in a security-sensitive context (processing secrets, handling PII, security-critical systems)
- If you're running user-supplied code

**Mitigations:**

- Use the `allowed_packages` parameter to maintain an allowlist: `NpmRuntime(allowed_packages={"lodash", "uuid"})`
- Run in a container or VM if security is a real concern
- Audit dependencies before using them
- Don't use `eval_js()` with untrusted code
- Keep Node.js and npm updated

## Limitations & Gotchas

**Browser packages won't work**: If an npm package requires `window`, `document`, or other DOM APIs, it will fail. Some packages include polyfills; if yours doesn't, you'll get a reference error.

**Prototype chains don't perfectly translate**: JavaScript has complex prototype chains and metaprogramming (proxies, getters, etc.). Standard patterns work fine, but exotic JS patterns might not translate perfectly to Python. If you hit this, use `proxy.to_python()` to serialize the object and inspect it.

**Async/await is automatic**: If a JS function is async, the Python call blocks until it resolves. No need to worry about promises; they're handled for you.

**No generators**: Generator and async generator functions aren't fully supported.

**Circular references**: If a JavaScript object refers back to itself, it can't be serialized to Python. The bridge will use object handles instead (you get a proxy, not the full object).

**GUI won't work**: There's no native GUI integration. If the JS library tries to open windows or interact with graphics, it won't work.

## License

MIT
