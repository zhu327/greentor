# coding: utf-8

from __future__ import absolute_import, print_function
import sys
import socket
import errno
import traceback

from pymysql import err
from pymysql.connections import DEBUG

from .green import AsyncSocket

__all__ = ('patch_pymysql', )


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
            if DEBUG: print(exc.traceback)
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


def patch_pymysql():
    sys.modules["pymysql"].connections.Connection.connect = _connect
    sys.modules["pymysql"].connections.Connection._read_bytes = _read_bytes
