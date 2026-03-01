"""CLI entry points for pynpm_bridge."""

from pathlib import Path

import click


@click.group()
def main():
    """pynpm - Use npm packages from Python."""
    pass


@main.command()
@click.argument("path", default=".")
def init(path):
    """Initialize a Node.js workspace for pynpm_bridge."""
    from pynpm_bridge.runtime import NpmRuntime

    workspace = NpmRuntime.init_workspace(path)
    click.echo(f"Initialized pynpm workspace at: {workspace}")


@main.command()
@click.argument("package_spec")
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def install(package_spec, workspace):
    """Install an npm package. Format: package[@version]"""
    from pynpm_bridge.runtime import NpmRuntime

    if package_spec.startswith("@"):
        rest = package_spec[1:]
        if "@" in rest.split("/", 1)[-1]:
            scope_and_name, version = rest.rsplit("@", 1)
            pkg_name = "@" + scope_and_name
        else:
            pkg_name = package_spec
            version = None
    elif "@" in package_spec:
        pkg_name, version = package_spec.rsplit("@", 1)
    else:
        pkg_name = package_spec
        version = None

    ws_path = Path(workspace).resolve()
    if not (ws_path / "package.json").exists():
        NpmRuntime.init_workspace(ws_path)

    runtime = NpmRuntime(workspace=ws_path)
    try:
        spec = runtime.install(pkg_name, version)
        click.echo(f"Installed: {spec}")
    finally:
        runtime.close()


@main.command(name="run-demo")
@click.option("--workspace", "-w", default=None, help="Workspace directory")
def run_demo(workspace):
    """Run a demo showing npm package usage from Python."""
    from pynpm_bridge.runtime import NpmRuntime
    from pynpm_bridge.exceptions import JavaScriptError

    click.echo("=" * 60)
    click.echo("pynpm_bridge Demo")
    click.echo("=" * 60)

    runtime = NpmRuntime(workspace=workspace)
    try:
        click.echo("\nInstalling lodash, dayjs, uuid...")
        runtime.install("lodash", "^4.17.21")
        runtime.install("dayjs", "^1.11.0")
        runtime.install("uuid", "^9.0.0")
        click.echo("Done.\n")

        lodash = runtime.require("lodash")
        click.echo(f'_.camelCase("hello world") = "{lodash.camelCase("hello world")}"')
        click.echo(f"_.chunk([1,2,3,4,5], 2) = {lodash.chunk([1,2,3,4,5], 2)}")

        dayjs = runtime.import_module("dayjs")
        d = dayjs("2026-01-01")
        click.echo(
            f'dayjs("2026-01-01").format("YYYY-MM-DD") = "{d.format("YYYY-MM-DD")}"'
        )

        uuid_mod = runtime.require("uuid")
        click.echo(f'uuid.v4() = "{uuid_mod.v4()}"')

        try:
            runtime.eval_js("throw new TypeError('demo error')")
        except JavaScriptError as e:
            click.echo(f"Caught {e.error_type}: {e.message}")

        click.echo("\n" + "=" * 60)
        click.echo("Demo complete!")
    finally:
        runtime.close()
