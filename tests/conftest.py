"""Shared test fixtures."""

import tempfile
from pathlib import Path

import pytest

from pynpm_bridge.runtime import NpmRuntime


@pytest.fixture(scope="session")
def shared_workspace():
    tmpdir = tempfile.mkdtemp(prefix="pynpm_test_")
    yield Path(tmpdir)


@pytest.fixture(scope="session")
def runtime_with_packages(shared_workspace):
    rt = NpmRuntime(workspace=shared_workspace, timeout=60.0)
    rt.install("lodash", "^4.17.21")
    rt.install("dayjs", "^1.11.0")
    rt.install("uuid", "^9.0.0")
    yield rt
    rt.close()


@pytest.fixture
def runtime():
    rt = NpmRuntime(timeout=60.0)
    yield rt
    rt.close()
