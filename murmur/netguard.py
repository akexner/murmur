"""Offline mode: while enabled, this process may only talk to the local machine (loopback).

Every outgoing socket connection to a non-loopback address is refused and counted, so
the Kanzlei profile is enforced by the app itself, not just by a promise.
"""
import ipaddress
import socket

blocked = 0
_flag = lambda: False
_installed = False


class OfflineError(OSError):
    pass


def _is_local(address) -> bool:
    try:
        host = address[0] if isinstance(address, tuple) else address
        if isinstance(host, bytes):
            host = host.decode()
        if host in ("localhost", ""):
            return True
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except Exception:
        return False  # hostnames / unparsable: not provably local


def install(flag):
    """Install the guard once; `flag()` is evaluated on every connection attempt."""
    global _flag, _installed
    _flag = flag
    if _installed:
        return
    _installed = True
    orig_connect, orig_ex = socket.socket.connect, socket.socket.connect_ex

    def guard(addr):
        global blocked
        if _flag() and getattr(addr, "__len__", None) is not None and not _is_local(addr):
            blocked += 1
            raise OfflineError("Offline mode: network connection blocked")

    def connect(self, address):
        guard(address)
        return orig_connect(self, address)

    def connect_ex(self, address):
        try:
            guard(address)
        except OfflineError:
            return 10013  # WSAEACCES
        return orig_ex(self, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
