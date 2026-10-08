import socket

import pytest


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """Tests must never reach a real API: any socket connection fails loudly."""
    def blocked(*a, **k):
        raise RuntimeError("network access is blocked in tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
