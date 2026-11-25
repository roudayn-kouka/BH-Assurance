"""Helpers for the audit hooks that keep the pilot scripts off the network."""

import sys
from pathlib import Path

_SOCKETPAIR_FUNCTIONS = {"socketpair", "_fallback_socketpair"}


def is_socketpair_emulation(endpoint) -> bool:
    """
    True when a loopback connect comes from socket.socketpair().

    Windows has no AF_UNIX socketpair: the standard library connects two 127.0.0.1 sockets
    instead, which asyncio does for its self-pipe (FastAPI's TestClient, anyio). Nothing
    leaves the host, so the pilots' network guards may let these through.
    """
    if not isinstance(endpoint, tuple) or endpoint[:1] != ("127.0.0.1",):
        return False
    frame = sys._getframe(1)
    while frame is not None:
        code = frame.f_code
        if code.co_name in _SOCKETPAIR_FUNCTIONS and Path(code.co_filename).name == "socket.py":
            return True
        frame = frame.f_back
    return False
