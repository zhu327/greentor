# -*- coding:utf-8 -*-
from __future__ import absolute_import
import sys
import socket
from gtornado.green import AsyncSocket


def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                      source_address=None, socket_options=None):
    """Connect to *address* and return the socket object.
    Convenience function.  Connect to *address* (a 2-tuple ``(host,
    port)``) and return the socket object.  Passing the optional
    *timeout* parameter will set the timeout on the socket instance
    before attempting to connect.  If no *timeout* is supplied, the
    global default timeout setting returned by :func:`getdefaulttimeout`
    is used.  If *source_address* is set it must be a tuple of (host, port)
    for the socket to bind as a source address before making the connection.
    An host of '' or port 0 tells the OS to use the default.
    """

    host, port = address
    if host.startswith('['):
        host = host.strip('[]')
    err = None
    for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)

            # If provided, set socket level options before connecting.
            # This is the only addition urllib3 makes to this function.
            _set_socket_options(sock, socket_options)

            # if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                # sock.settimeout(timeout)
            # if source_address:
                # sock.bind(source_address)
            iostream = AsyncSocket(sock)
            iostream.connect((host, port))
            return iostream

        except socket.error as e:
            err = e
            if sock is not None:
                iostream.close()
                sock = iostream = None

    if err is not None:
        raise err

    raise socket.error("getaddrinfo returns an empty list")


def _set_socket_options(sock, options):
    if options is None:
        return

    for opt in options:
        sock.setsockopt(*opt)

def patch_requests():
    sys.modules["requests"].packages.urllib3.util.connection.create_connection = create_connection
