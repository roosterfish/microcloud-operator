"""Pytest configuration for the MicroCloud charm integration tests.

The tests exercise a MicroCloud cluster deployed by ``tests/integration/vms.py``
and a charm built with ``charmcraft pack``. They need an LXD-backed Juju
controller and, for the COS scenarios, a Canonical K8s-backed one.
"""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.integration.vms import VMEnvironment

logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--charm",
        default=os.environ.get("MICROCLOUD_CHARM_PATH", ""),
        action="store",
        help="Path to a charm built with `charmcraft pack`.",
    )
    parser.addoption(
        "--lxd-controller",
        default=os.environ.get("LXD_CONTROLLER", ""),
        action="store",
        help="Juju controller backed by LXD. Defaults to $LXD_CONTROLLER.",
    )
    parser.addoption(
        "--k8s-controller",
        default=os.environ.get("K8S_CONTROLLER", ""),
        action="store",
        help="Juju controller backed by Canonical K8s. Defaults to $K8S_CONTROLLER.",
    )
    parser.addoption(
        "--constraints",
        default="",
        action="store",
        help='Space-separated Juju model constraints, e.g. "mem=2G".',
    )
    parser.addoption(
        "--num-units",
        default=1,
        type=int,
        action="store",
        help="Default number of MicroCloud units for the test scenarios.",
    )


@pytest.fixture(scope="module")
def charm_path(request: pytest.FixtureRequest) -> Path:
    path = request.config.getoption("--charm")
    assert path, "--charm must be provided; build the charm with `charmcraft pack` first"
    charm = Path(path)
    assert charm.is_file(), f"--charm points at a missing file: {charm}"
    # Return a Path: jubilant only treats pathlib.Path as a local charm file,
    # so a bare filename would be looked up on Charmhub instead.
    return charm.absolute()


@pytest.fixture(scope="module")
def lxd_controller(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("--lxd-controller")


@pytest.fixture(scope="module")
def k8s_controller(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("--k8s-controller")


@pytest.fixture(scope="module")
def constraints(request: pytest.FixtureRequest) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for constraint in request.config.getoption("--constraints").split(" "):
        if not constraint:
            continue
        key, value = constraint.split("=", 1)
        parsed[key] = value
    return parsed


@pytest.fixture(scope="module")
def num_units(request: pytest.FixtureRequest) -> int:
    count = request.config.getoption("--num-units")
    assert count >= 1, "--num-units must be at least 1"
    return count


@pytest.fixture(scope="session")
def vm_env() -> Iterator[VMEnvironment]:
    """Provision the shared LXD workspace, SSH key and optionally the uplink network."""
    env = VMEnvironment()
    try:
        yield env
    finally:
        env.cleanup()


@pytest.fixture(scope="module", autouse=True)
def report_resources(request: pytest.FixtureRequest) -> Iterator[None]:
    """Log free disk after each module, while the live log still streams."""
    yield
    usage = shutil.disk_usage("/")
    logger.info(
        "After %s: %.1f GiB of %.1f GiB disk free",
        request.module.__name__,
        usage.free / 2**30,
        usage.total / 2**30,
    )
