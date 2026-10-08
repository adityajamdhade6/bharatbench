import importlib

import pytest

import bharatbench


def test_version():
    assert bharatbench.__version__ == "0.1.0"


@pytest.mark.parametrize("sub", ["adapters", "scoring", "runner"])
def test_subpackages_import(sub):
    assert importlib.import_module(f"bharatbench.{sub}")
