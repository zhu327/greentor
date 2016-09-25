# coding: utf-8

from __future__ import absolute_import
import sys
import socket
import errno
import traceback
import time

from pymysql import err
from pymysql.connections import DEBUG, Connection

from .green import AsyncSocket, Pool, green

__all__ = ('patch_pymysql', 'ConnectionPool')


def _connect(self, sock=None):
    try:
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock = AsyncSocket(sock)
            sock.set_connecttimeout(self.connect_timeout)
            sock.connect((self.host, self.port))
            sock.set_nodelay(True)
        self._sock = sock
        # self._rfile = _makefile(sock, 'rb')
        self._rfile = sock
        self._next_seq_id = 0

        self._get_server_information()
        self._request_authentication()

        if self.sql_mode is not None:
            c = self.cursor()
            c.execute("SET sql_mode=%s", (self.sql_mode, ))

        if self.init_command is not None:
            c = self.cursor()
            c.execute(self.init_command)
            c.close()
            self.commit()

        if self.autocommit_mode is not None:
            self.autocommit(self.autocommit_mode)
    except BaseException as e:
        self._rfile = None
        if sock is not None:
            try:
                sock.close()
            except:
                pass

        if isinstance(e, (OSError, IOError, socket.error)):
            exc = err.OperationalError(
                2003, "Can't connect to MySQL server on %r (%s)" % (
                    self.host, e))
            # Keep original exception and traceback to investigate error.
            exc.original_exception = e
            exc.traceback = traceback.format_exc()
            if DEBUG: print exc.traceback
            raise exc

        # If e is neither DatabaseError or IOError, It's a bug.
        # But raising AssertionError hides original error.
        # So just reraise it.
        raise


def _read_bytes(self, num_bytes):
    self._sock.set_readtimeout(self._read_timeout)
    while True:
        try:
            data = self._rfile.read(num_bytes)
            break
        except (IOError, OSError) as e:
            if e.errno == errno.EINTR:
                continue
            raise err.OperationalError(
                2013,
                "Lost connection to MySQL server during query (%s)" % (e, ))
    if len(data) < num_bytes:
        raise err.OperationalError(
            2013, "Lost connection to MySQL server during query")
    return data


class ConnectionPool(Pool):
    def __init__(self, max_size=32, keep_alive=7200, mysql_params={}):
        super(ConnectionPool, self).__init__(max_size=max_size, params=mysql_params)
        self._keep_alive = keep_alive # 为避免连接自动断开，配置连接ping周期

    def create_raw_conn(self):
        conn = Connection(**self._conn_params)
        if self._keep_alive:
            self._ioloop.add_timeout(time.time()+self._keep_alive, self._ping, conn)
        return conn

    @green
    def _ping(self, conn):
        if conn in self._pool:
            self._pool.remove(conn)
            conn.ping()
            self.release(conn)
        self._ioloop.add_timeout(time.time()+self._keep_alive, self._ping, conn)


def patch_pymysql():
    sys.modules["pymysql"].connections.Connection.connect = _connect
    sys.modules["pymysql"].connections.Connection._read_bytes = _read_bytes
