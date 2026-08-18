"""Smoke test proving the ScrollSense package and modules import cleanly."""

import importlib
import pytest


def test_package_import():
    """Verify that root package imports cleanly and has a version."""
    import scrollsense
    assert scrollsense.__version__ == "0.1.0"


@pytest.mark.parametrize(
    "submodule",
    [
        "scrollsense.domain",
        "scrollsense.graph",
        "scrollsense.signals",
        "scrollsense.persona",
        "scrollsense.retrieval",
        "scrollsense.ranking",
        "scrollsense.gates",
        "scrollsense.feedback",
        "scrollsense.evaluation",
        "scrollsense.api",
    ],
)
def test_submodules_import(submodule: str):
    """Verify that all architectural submodules are importable."""
    module = importlib.import_module(submodule)
    assert module is not None
