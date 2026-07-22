"""Smoke test: the package imports from an installed (src-layout) environment.

Replace with real tests; Constitution C3 requires test-first for core logic.
"""


def test_package_imports():
    import importlib

    assert importlib.import_module("{{package}}").__version__
