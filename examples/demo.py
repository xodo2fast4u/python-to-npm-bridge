#!/usr/bin/env python3
"""pynpm_bridge demo script."""

from pynpm_bridge.runtime import NpmRuntime
from pynpm_bridge.exceptions import JavaScriptError


def main():
    print("=" * 60)
    print("pynpm_bridge Demo")
    print("=" * 60)

    with NpmRuntime() as runtime:
        print("\nInstalling lodash, dayjs, uuid...")
        runtime.install("lodash", "^4.17.21")
        runtime.install("dayjs", "^1.11.0")
        runtime.install("uuid", "^9.0.0")
        print("Done.\n")

        _ = runtime.require("lodash")
        print(f'_.camelCase("hello world") = "{_.camelCase("hello world")}"')
        print(f"_.chunk([1,2,3,4,5], 2) = {_.chunk([1,2,3,4,5], 2)}")
        print(f"_.uniq([1,1,2,3,3,4]) = {_.uniq([1,1,2,3,3,4])}")
        print(f"_.sum([1,2,3,4,5]) = {_.sum([1,2,3,4,5])}")

        dayjs = runtime.import_module("dayjs")
        d = dayjs("2026-01-01")
        print(
            f'\ndayjs("2026-01-01").format("YYYY-MM-DD") = "{d.format("YYYY-MM-DD")}"'
        )

        uuid_mod = runtime.require("uuid")
        print(f'\nuuid.v4() = "{uuid_mod.v4()}"')
        print(f'uuid.v4() = "{uuid_mod.v4()}"')

        print("\nError handling:")
        try:
            runtime.eval_js("throw new TypeError('demo error')")
        except JavaScriptError as e:
            print(f"  Caught {e.error_type}: {e.message}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
