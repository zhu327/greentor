# -*- coding:utf-8 -*-
from __future__ import absolute_import
from gtornado import AsyncSocket, green
import socket

__all__ = ("MemCachePool", )


class AsyncSocketModule(AsyncSocket):
    AF_INET = socket.AF_INET
    SOCK_STREAM = socket.SOCK_STREAM
    def __init__(self, sock_inet, sock_type):
        self._sock = socket.socket(sock_inet, sock_type)
        super(AsyncSocketModule, self).__init__(self._sock)

    @staticmethod
    def socket(sock_inet, sock_type):
        return AsyncSocketModule(sock_inet, sock_type)

    def settimeout(self, timeout):
        pass

    def setsockopt(self, proto, option, value):
        self.set_nodelay(value)

    def recv(self, nbytes):
        return self.read(nbytes, partial=True)


from pymemcache.client.base import Client


class MemCachePool(green.Pool):
    def create_raw_conn(self):
        servers = self._conn_params["servers"]
        return Client(servers, socket_module=AsyncSocketModule)

    def _close_all(self):
        for conn in self._pool:
            conn.quit()
        self._pool = None            
