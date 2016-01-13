# -*- coding:utf-8 -*-
from __future__ import absolute_import
import socket
from redis.connection import Connection, ConnectionPool
from gtornado import AsyncSocket

__all__ = ("RedisConnectionPool", )

class AsyncRedisConnection(Connection):

    def _connect(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            iostream = AsyncSocket(sock)
            iostream.set_nodelay(True)
            iostream.connect((self.host, self.port), self.socket_connect_timeout)
            return iostream
        except:
            if sock is not None:
                iostream.close()


class RedisConnectionPool(ConnectionPool):
    def __init__(self, **conn_args):
        conn_args.update({"connection_class": AsyncRedisConnection})
        super(RedisConnectionPool, self).__init__(**conn_args)
