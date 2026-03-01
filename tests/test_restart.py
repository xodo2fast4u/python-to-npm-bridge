import time
from pynpm_bridge.runtime import NpmRuntime


def test_worker_restart_after_crash(runtime):
    runtime.install("lodash", "^4.17.21")
    lodash = runtime.require("lodash")
    assert lodash.camelCase("hello world") == "helloWorld"

    # Kill the worker — all old handles become invalid
    runtime._worker._kill_worker()
    time.sleep(0.5)

    # Reassigning the same name causes the original proxy to be garbage
    # collected.  Prior to the fix this would send a ``releaseHandle`` for
    # "h_1" to the newly-started worker (which also used "h_1") and would
    # break the subsequent access.  The generation-tracking logic should
    # prevent that.
    lodash = runtime.require("lodash")
    assert lodash.camelCase("foo bar") == "fooBar"


def test_worker_restart_preserves_packages(runtime):
    runtime.install("lodash", "^4.17.21")
    lodash = runtime.require("lodash")
    assert lodash.isString("test") is True

    runtime._worker._kill_worker()
    time.sleep(0.5)

    # Packages are on disk; re-require works after restart
    lodash = runtime.require("lodash")
    assert lodash.isNumber(42) is True


def test_release_not_sent_for_stale_proxy(runtime):
    """Old proxies should not release a handle after the worker restarts."""
    runtime.install("lodash", "^4.17.21")
    lodash = runtime.require("lodash")
    assert lodash.camelCase("a b") == "aB"

    runtime._worker._kill_worker()
    time.sleep(0.5)

    # drop the only reference and run the collector; prior to the fix this
    # would send ``releaseHandle`` to the *new* worker with id "h_1".
    del lodash
    import gc

    gc.collect()

    lodash = runtime.require("lodash")
    assert lodash.camelCase("c d") == "cD"


def test_graceful_shutdown(runtime):
    runtime.install("lodash", "^4.17.21")
    lodash = runtime.require("lodash")
    assert lodash.camelCase("test case") == "testCase"
    runtime.close()
    assert runtime._closed is True


def test_context_manager():
    with NpmRuntime(timeout=60.0) as rt:
        rt.install("lodash", "^4.17.21")
        lodash = rt.require("lodash")
        assert lodash.camelCase("context manager") == "contextManager"
    assert rt._closed is True
