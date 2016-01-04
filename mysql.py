# -*- coding:utf-8 -*-
from __future__ import absolute_import
import sys
import socket
from tornado.ioloop import IOLoop
from pymysql.connections import Connection
from gtornado import AsyncSocket, green


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
    def __init__(self, max_size=-1):
        self._maxsize = max_size
        self._pool = []
        self._started = False
        self._ioloop = IOLoop.current()
        self._event = green.Event()
        self._ioloop.add_future(
                                green.spawn(self.start), 
                                lambda future: future)

    def create_raw_conn(self):
        return AsyncConnection(
                host="10.86.11.116", 
                port=3306,
                user="root",
                db="mywork",
                password="powerall",
                charset="utf8"
                )
 
    def init_pool(self):
        for index in range(self._maxsize):
            conn = self.create_raw_conn()
            self._pool.append(conn)

    @property
    def size(self):
        return len(self._pool)

    def get_conn(self):
        if self.size > 0:
            return self._pool.pop(0)
        else:
            raise Exception("no available connections", self.size)

    def return_back(self, conn):
        self._pool.append(conn)

    def quit(self):
        self._started = False
        self._event.set()

    def _close_all(self):
        for conn in self._pool:
            conn.close()
        self._pool =  None           

    def start(self):
        self.init_pool()
        self._started = True
        self._event.wait()
        self._close_all()


ConnectionPool = MySQLConnectionPool(100)


class ConnectionProxy(object):
    def __init__(self, raw_conn):
        self._raw_conn = raw_conn

    def close(self):
        ConnectionPool.release(self._raw_conn)

    def __getattr__(self, key):
        if key == "close":
            return self.close
        else:
            return getattr(self._raw_conn, key)


def connect(*args, **kwargs):
    raw_conn = ConnectionPool.get_conn()
    return ConnectionProxy(raw_conn)

def patch_pymysql():
    sys.modules["pymysql"].connect = connect
