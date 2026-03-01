import { createRequire } from "module";
import { join } from "path";
import readline from "readline";

const handles = new Map();
let hc = 0;

function store(v) {
  if (v === null || v === undefined) return null;
  const t = typeof v;
  if (t === "boolean" || t === "number" || t === "string" || t === "bigint")
    return null;
  const id = "h_" + ++hc;
  handles.set(id, v);
  return id;
}

function get(id) {
  if (!handles.has(id)) throw new Error("Invalid handle: " + id);
  return handles.get(id);
}

function release(id) {
  handles.delete(id);
}

/**
 * Check whether a plain object has any function-valued own properties.
 */
function hasAnyFunctionValues(obj) {
  const keys = Object.keys(obj);
  for (let i = 0; i < keys.length; i++) {
    try {
      if (typeof obj[keys[i]] === "function") return true;
    } catch (e) {
      /* getter threw */
    }
  }
  return false;
}

function ser(v, d, forceHandle) {
  if (d === undefined) d = 0;
  if (forceHandle === undefined) forceHandle = false;

  if (v === undefined) return { __type__: "undefined" };
  if (v === null) return null;
  const t = typeof v;
  if (t === "boolean" || t === "string") return v;
  if (t === "number") {
    if (Number.isNaN(v)) return { __type__: "float_special", value: "NaN" };
    if (!Number.isFinite(v))
      return {
        __type__: "float_special",
        value: v > 0 ? "Infinity" : "-Infinity",
      };
    return v;
  }
  if (t === "bigint") return { __type__: "bigint", value: v.toString() };
  if (t === "symbol")
    return {
      __type__: "handle",
      handleId: store(v),
      jsType: "symbol",
      preview: v.toString(),
    };
  if (t === "function") {
    return {
      __type__: "handle",
      handleId: store(v),
      jsType: "function",
      preview: "[Function: " + (v.name || "anonymous") + "]",
    };
  }

  // Force handle mode: always wrap as handle regardless of type
  if (forceHandle) {
    return makeHandle(v);
  }

  if (v instanceof Date) return { __type__: "date", iso: v.toISOString() };
  if (Buffer.isBuffer(v) || v instanceof Uint8Array)
    return { __type__: "bytes", data: Buffer.from(v).toString("base64") };
  if (v instanceof Error)
    return {
      __type__: "error",
      message: v.message,
      stack: v.stack || "",
      errorType: (v.constructor && v.constructor.name) || "Error",
    };
  if (v instanceof Promise)
    return {
      __type__: "handle",
      handleId: store(v),
      jsType: "promise",
      preview: "[Promise]",
    };

  if (Array.isArray(v)) {
    if (d > 6) return makeHandle(v);
    try {
      return v.map(function (x) {
        return ser(x, d + 1);
      });
    } catch (e) {
      return makeHandle(v);
    }
  }

  // Object
  const proto = Object.getPrototypeOf(v);
  const plain = proto === null || proto === Object.prototype;

  if (plain && d <= 4) {
    // If the object has any function-valued properties, store as handle
    // so Python gets a JsProxy and can call methods
    if (hasAnyFunctionValues(v)) {
      return makeHandle(v);
    }

    try {
      const keys = Object.keys(v);
      if (keys.length <= 500) {
        const r = {};
        let ok = true;
        for (let i = 0; i < keys.length; i++) {
          if (v[keys[i]] === v) {
            ok = false;
            break;
          }
          r[keys[i]] = ser(v[keys[i]], d + 1);
        }
        if (ok) return r;
      }
    } catch (e) {}
  }

  return makeHandle(v);
}

function makeHandle(v) {
  const hid = store(v);
  let jt = "object",
    pv = "[Object]";
  try {
    const cn = (v.constructor && v.constructor.name) || "Object";
    jt = cn.toLowerCase();
    pv = "[" + cn + "]";
  } catch (e) {}
  const props = [];
  try {
    const seen = new Set();
    let cur = v;
    while (cur && cur !== Object.prototype) {
      for (const n of Object.getOwnPropertyNames(cur)) {
        if (!n.startsWith("_") && !seen.has(n)) {
          seen.add(n);
          props.push(n);
        }
      }
      cur = Object.getPrototypeOf(cur);
    }
  } catch (e) {}
  return {
    __type__: "handle",
    handleId: hid,
    jsType: jt,
    preview: pv,
    props: props.length > 0 ? props.slice(0, 200) : undefined,
  };
}

function deser(v) {
  if (v === null || v === undefined) return v;
  if (typeof v !== "object") return v;
  if (Array.isArray(v)) return v.map(deser);
  const t = v.__type__;
  if (t === "bigint") return BigInt(v.value);
  if (t === "bytes") return Buffer.from(v.data, "base64");
  if (t === "date") return new Date(v.iso);
  if (t === "undefined") return undefined;
  if (t === "float_special") {
    if (v.value === "NaN") return NaN;
    if (v.value === "Infinity") return Infinity;
    if (v.value === "-Infinity") return -Infinity;
  }
  if (t === "handle_ref") return get(v.handleId);
  const r = {};
  for (const k of Object.keys(v)) r[k] = deser(v[k]);
  return r;
}

const cwd = process.cwd();
const localRequire = createRequire(join(cwd, "noop.js"));

async function handle(msg) {
  const m = msg.method,
    p = msg.params || {},
    id = msg.id;
  try {
    let result;
    if (m === "require") {
      let mod;
      try {
        mod = localRequire(p.moduleName);
      } catch (re) {
        try {
          const imp = await import(p.moduleName);
          if (imp && imp.default !== undefined) {
            const named = Object.keys(imp).filter(
              (k) => k !== "default" && k !== "__esModule",
            );
            mod = named.length === 0 ? imp.default : imp;
          } else mod = imp;
        } catch (ie) {
          throw re;
        }
      }
      result = ser(mod);
    } else if (m === "import") {
      let mod = await import(p.moduleName);
      if (mod && mod.default !== undefined) {
        const named = Object.keys(mod).filter(
          (k) => k !== "default" && k !== "__esModule",
        );
        if (named.length === 0) {
          mod = mod.default;
        } else if (typeof mod.default === "function") {
          const def = mod.default;
          const w = function () {
            return def.apply(this, arguments);
          };
          w.prototype = def.prototype;
          for (const k of Object.keys(mod)) {
            if (k !== "default")
              try {
                w[k] = mod[k];
              } catch (e) {}
          }
          mod = w;
        }
      }
      result = ser(mod);
    } else if (m === "getProperty") {
      const obj = get(p.handleId);
      let val = obj[p.property];
      if (typeof val === "function") val = val.bind(obj);
      result = ser(val);
    } else if (m === "setProperty") {
      get(p.handleId)[p.property] = deser(p.value);
      result = null;
    } else if (m === "call") {
      const fn = get(p.handleId);
      if (typeof fn !== "function") throw new TypeError("Not callable");
      let ret = fn.apply(null, (p.args || []).map(deser));
      if (ret && typeof ret === "object" && typeof ret.then === "function")
        ret = await ret;
      result = ser(ret);
    } else if (m === "callMethod") {
      const obj = get(p.handleId);
      if (typeof obj[p.method] !== "function")
        throw new TypeError(p.method + " is not a function");
      let ret = obj[p.method].apply(obj, (p.args || []).map(deser));
      if (ret && typeof ret === "object" && typeof ret.then === "function")
        ret = await ret;
      result = ser(ret);
    } else if (m === "construct") {
      const C = get(p.handleId);
      if (typeof C !== "function") throw new TypeError("Not a constructor");
      const instance = new C(...(p.args || []).map(deser));
      // Always return as handle so Python can call methods on the instance
      result = ser(instance, 0, true);
    } else if (m === "serialize") {
      const obj = get(p.handleId);
      try {
        result = JSON.parse(
          JSON.stringify(obj, (k, v) =>
            typeof v === "bigint"
              ? { __type__: "bigint", value: v.toString() }
              : v,
          ),
        );
      } catch (e) {
        result = ser(obj, 0);
      }
    } else if (m === "releaseHandle") {
      release(p.handleId);
      result = null;
    } else if (m === "eval") {
      const ie = eval;
      let ret = ie(p.code);
      if (ret && typeof ret === "object" && typeof ret.then === "function")
        ret = await ret;
      result = ser(ret);
    } else if (m === "shutdown") {
      if (id != null) resp(id, null);
      process.exit(0);
      return;
    } else {
      throw new Error("Unknown method: " + m);
    }
    if (id != null) resp(id, result);
  } catch (err) {
    if (id != null) errResp(id, err);
  }
}

function resp(id, r) {
  process.stdout.write(
    JSON.stringify({ jsonrpc: "2.0", id, result: r !== undefined ? r : null }) +
      "\n",
  );
}
function errResp(id, e) {
  process.stdout.write(
    JSON.stringify({
      jsonrpc: "2.0",
      id,
      error: {
        message: (e && e.message) || String(e),
        stack: (e && e.stack) || "",
        errorType: (e && e.constructor && e.constructor.name) || "Error",
      },
    }) + "\n",
  );
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });
process.stdout.write(JSON.stringify({ type: "ready" }) + "\n");

rl.on("line", async (line) => {
  const s = line.trim();
  if (!s) return;
  try {
    await handle(JSON.parse(s));
  } catch (e) {
    try {
      const p = JSON.parse(s);
      if (p.id) errResp(p.id, e);
    } catch (e2) {}
  }
});
rl.on("close", () => process.exit(0));
process.on("uncaughtException", (e) =>
  process.stderr.write("Uncaught: " + (e ? e.stack || e.message : "") + "\n"),
);
process.on("unhandledRejection", (e) =>
  process.stderr.write("Unhandled: " + String(e) + "\n"),
);
