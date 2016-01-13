# -*- coding:utf-8 -*-
from __future__ import absolute_import
import sys
import socket
from gtornado.green import AsyncSocket


def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                      source_address=None, socket_options=None):
    try:
        host, port = address
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        iostream = AsyncSocket(sock)
        iostream.connect((host, port))
        iostream.set_nodelay(True)
        return iostream
    except:
        if sock is not None:
            iostream.close()
            sock = iostream = None

def patch_requests():
    sys.modules["requests"].packages.urllib3.util.connection.create_connection = create_connection
