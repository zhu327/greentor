# -*- coding:utf-8 -*-
from __future__ import absolute_import
import sys
import socket
from redis.connection import Connection, ConnectionPool
from gtornado import AsyncSocket, green, utils

__all__ = ("RedisConnectionPool", )

class AsyncRedisConnection(Connection):

    def _connect(self):
        "Create a TCP socket connection"
        # we want to mimic what socket.create_connection does to support
        # ipv4/ipv6, but we want to set options prior to calling
        # socket.connect()
        err = None
        for res in socket.getaddrinfo(self.host, self.port, 0,
                                      socket.SOCK_STREAM):
            family, socktype, proto, canonname, socket_address = res
            sock = None
            try:
                sock = socket.socket(family, socktype, proto)
                # TCP_NODELAY
                iostream = AsyncSocket(sock)
                iostream.set_nodelay(True)

                # TCP_KEEPALIVE
               # if self.socket_keepalive:
               #     sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
               #     for k, v in iteritems(self.socket_keepalive_options):
               #         sock.setsockopt(socket.SOL_TCP, k, v)

                # connect
                iostream.connect(socket_address, self.socket_connect_timeout)

                return iostream

            except socket.error as _:
                err = _
                if sock is not None:
                    iostream.close()

        if err is not None:
            raise err
        raise socket.error("socket.getaddrinfo returned an empty list")


class RedisConnectionPool(ConnectionPool):
    def __init__(self, **conn_args):
        conn_args.update({"connection_class": AsyncRedisConnection})
        super(RedisConnectionPool, self).__init__(**conn_args)
