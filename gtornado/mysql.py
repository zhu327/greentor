# -*- coding:utf-8 -*-
from __future__ import absolute_import
import sys
import socket
from pymysql.connections import Connection
from gtornado import AsyncSocket, green, utils

__all__ = ("AsyncConnection", "MySQLConnectionPool", "patch_pymysql")

class AsyncConnection(Connection):
    def __init__(self, *args, **kwargs):
        super(AsyncConnection, self).__init__(*args, **kwargs)

    def connect(self, sock=None):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = AsyncSocket(sock)
            self.socket.connect((self.host, self.port))
            self.socket.set_nodelay(True)
            self._rfile = self.socket
            self._get_server_information()
            self._request_authentication()

            if self.sql_mode is not None:
                c = self.cursor()
                c.execute("SET sql_mode=%s", (self.sql_mode,))

            if self.init_command is not None:
                c = self.cursor()
                c.execute(self.init_command)
                c.close()
                self.commit()

            if self.autocommit_mode is not None:
                self.autocommit(self.autocommit_mode)
        except socket.error:
            if self.socket:
                self.socket.close()
            raise


class MySQLConnectionPool(green.Pool):
    __metaclass__ = utils.Singleton

    def __init__(self, max_size=-1, mysql_params={}):
        super(MySQLConnectionPool, self).__init__(max_size, mysql_params)

    def create_raw_conn(self):
        return AsyncConnection(
                host=self._conn_params["host"],
                port=self._conn_params["port"],
                user=self._conn_params["username"],
                db=self._conn_params["db"],
                password=self._conn_params["password"],
                charset=self._conn_params.get("charset", "utf8")
                )


class ConnectionProxy(object):
    def __init__(self, raw_conn):
        self._raw_conn = raw_conn
        self._pool = MySQLConnectionPool()

    def close(self):
        self._pool.release(self._raw_conn)

    def __getattr__(self, key):
        print("call method", key)
        if key == "close":
            return self.close
        else:
            return getattr(self._raw_conn, key)


def connect(*args, **kwargs):
    pool = MySQLConnectionPool()
    raw_conn = pool.get_conn()
    return ConnectionProxy(raw_conn)

def patch_pymysql():
    sys.modules["pymysql"].connect = connect
