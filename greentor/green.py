# coding: utf-8

from __future__ import absolute_import
import sys
import socket
import time
import errno
import greenlet
from functools import wraps
from collections import deque
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from tornado.ioloop import IOLoop
from tornado.concurrent import Future
from tornado.gen import coroutine, Return
from tornado.netutil import Resolver
from tornado.iostream import (IOStream as BaseIOStream, StreamClosedError,
                              _ERRNO_WOULDBLOCK)

IS_PYPY = False
try:
    import __pypy__
    __pypy__
    IS_PYPY = True
except:
    pass


def enable_debug():
    if IS_PYPY:
        sys.stderr.write("settrace api unsupported on pypy")
        sys.stderr.flush()
        return

    import inspect

    def trace_green(event, args):
        src, target = args
        if event == "switch":
            print("from %s switch to %s" % (src, target))
        elif event == "throw":
            print("from %s throw exception to %s" % (src, target))

        if src.gr_frame:
            tracebacks = inspect.getouterframes(src.gr_frame)
            buff = []
            for traceback in tracebacks:
                srcfile, lineno, func_name, codesample = traceback[1:-1]
                trace_line = '''File "%s", line %d, in %s\n%s '''
                buff.append(trace_line %
                            (srcfile, lineno, func_name, "".join(codesample)))

            print("".join(buff))

    greenlet.settrace(trace_green)


class GreenTask(greenlet.greenlet):
    def __init__(self, run, *args, **kwargs):
        super(GreenTask, self).__init__()
        self._run = run
        self._args = args
        self._kwargs = kwargs
        self._future = Future()
        self._result = None
        self._exc_info = ()

    @property
    def args(self):
        return self._args

    @property
    def kwargs(self):
        return self._kwargs

    def run(self):
        try:
            timeout = self.kwargs.pop("timeout", 0)
            if timeout:
                timer = Timeout(timeout)
                timer.start()
            self._result = self._run(*self.args, **self.kwargs)
            self._future.set_result(self._result)
        except:
            self._exc_info = sys.exc_info()
            self._future.set_exc_info(self._exc_info)
        finally:
            if timeout:
                timer.cancel()

    def start(self):
        self.switch()

    def __str__(self):
        func_name = "%s of %s " % (self._run.__name__, self._run.__module__)
        return "<greenlet %s at %s>" % (func_name, hex(id(self)))

    def __repr__(self):
        return self.__str__()

    def wait(self):
        return self._future

    @classmethod
    def spawn(cls_green, *args, **kwargs):
        task = cls_green(*args, **kwargs)
        task.start()
        return task


def synclize(func):
    coro = coroutine(func)

    @wraps(func)
    def _sync_call(*args, **kwargs):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main, "only run in child greenlet"

        def callback(future):
            if future.exc_info():
                child_gr.throw(*future.exc_info())
            elif future.exception():
                child_gr.throw(future.exception())
            else:
                child_gr.switch(future.result())

        IOLoop.current().add_future(coro(*args, **kwargs), callback)
        return main.switch()

    return _sync_call


def spawn(callable_obj, *args, **kwargs):
    return GreenTask.spawn(callable_obj, *args, **kwargs).wait()


def green(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return GreenTask.spawn(func, *args, **kwargs).wait()

    return wrapper


class Waiter(object):
    def __init__(self):
        self._greenlet = greenlet.getcurrent()
        self._main = self._greenlet.parent

    @property
    def greenlet(self):
        return self._greenlet

    def switch(self, value):
        self._greenlet.switch(value)

    def throw(self, *exc_info):
        self._greenlet.throw(*exc_info)

    def get(self):
        return self._main.switch()

    def clear(self):
        pass


def sleep(seconds):
    waiter = Waiter()
    unique = object()
    IOLoop.current().add_timeout(time.time() + seconds, waiter.switch, unique)
    waiter.get()


class TimeoutException(Exception):

    pass


class Timeout(object):
    def __init__(self, deadline, ex=TimeoutException):
        self._greenlet = greenlet.getcurrent()
        self._ex = ex
        self._callback = None
        self._deadline = deadline
        self._delta = time.time() + deadline
        self._ioloop = IOLoop.current()

    def start(self, callback=None):
        errmsg = "%s timeout, deadline is %d seconds" % (str(self._greenlet),
                                                         self._deadline)
        if callback:
            self._callback = self._ioloop.add_timeout(self._delta, callback,
                                                      self._ex(errmsg))
        else:
            self._callback = self._ioloop.add_timeout(
                self._delta, self._greenlet.throw, self._ex(errmsg))

    def cancel(self):
        assert self._callback, "Timeout not started"
        self._ioloop.remove_timeout(self._callback)
        self._greenlet = None


class IOStream(BaseIOStream):
    def _handle_events(self, fd, events):
        if self._closed:
            return
        try:
            if self._connecting:
                self._handle_connect()
            if self._closed:
                return
            if events & self.io_loop.READ:
                self._handle_read()
            if self._closed:
                return
            if events & self.io_loop.WRITE:
                self._handle_write()
            if self._closed:
                return
            if events & self.io_loop.ERROR:
                self.error = self.get_fd_error()
                self.io_loop.add_callback(self.close)
                return
        except Exception:
            self.close(exc_info=True)
            raise

    def _handle_connect(self):
        super(IOStream, self)._handle_connect()

        if not self.closed():
            self._state = self.io_loop.ERROR | self.io_loop.READ
            self.io_loop.update_handler(self.fileno(), self._state)

    def _handle_read(self):
        chunk = True

        while True:
            try:
                chunk = self.socket.recv(self.read_chunk_size)
                if not chunk:
                    break
                self._read_buffer.append(chunk)
                self._read_buffer_size += len(chunk)
            except (socket.error, IOError, OSError) as e:
                en = e.errno if hasattr(e, 'errno') else e.args[0]
                if en in _ERRNO_WOULDBLOCK:
                    break

                if en == errno.EINTR:
                    continue

                self.close(exc_info=True)
                return

        if self._read_future is not None and self._read_buffer_size >= self._read_bytes:
            future, self._read_future = self._read_future, None
            data = b"".join(self._read_buffer)
            self._read_buffer.clear()
            self._read_buffer_size = 0
            self._read_bytes = 0
            future.set_result(data)

        if not chunk:
            self.close()
            return

    def read(self, num_bytes):
        assert self._read_future is None, "Already reading"
        if self._closed:
            raise StreamClosedError(real_error=self.error)

        future = self._read_future = Future()
        self._read_bytes = num_bytes
        self._read_partial = False
        if self._read_buffer_size >= self._read_bytes:
            future, self._read_future = self._read_future, None
            data = b"".join(self._read_buffer)
            self._read_buffer.clear()
            self._read_buffer_size = 0
            self._read_bytes = 0
            future.set_result(data)
        return future

    read_bytes = read

    def _handle_write(self):
        while self._write_buffer:
            try:
                data = self._write_buffer.popleft()
                num_bytes = self.socket.send(data)
                self._write_buffer_size -= num_bytes
                if num_bytes < len(data):
                    self._write_buffer.appendleft(data[num_bytes:])
                    return
            except (socket.error, IOError, OSError) as e:
                en = e.errno if hasattr(e, 'errno') else e.args[0]
                if en in _ERRNO_WOULDBLOCK:
                    self._write_buffer.appendleft(data)
                    break

                self.close(exc_info=True)
                return

        if not self._write_buffer:
            if self._state & self.io_loop.WRITE:
                self._state = self._state & ~self.io_loop.WRITE
                self.io_loop.update_handler(self.fileno(), self._state)

    def write(self, data):
        assert isinstance(data, bytes)
        if self._closed:
            raise StreamClosedError(real_error=self.error)

        if data:
            self._write_buffer.append(data)
            self._write_buffer_size += len(data)

        if not self._connecting:
            self._handle_write()
            if self._write_buffer:
                if not self._state & self.io_loop.WRITE:
                    self._state = self._state | self.io_loop.WRITE
                    self.io_loop.update_handler(self.fileno(), self._state)


class AsyncSocket(object):
    def __init__(self, sock):
        self._iostream = IOStream(sock)
        self._resolver = Resolver()
        self._readtimeout = 0
        self._connecttimeout = 0
        self._rbuffer = StringIO(b'')
        self._rbuffer_size = 0

    def set_readtimeout(self, timeout):
        self._readtimeout = timeout

    def set_connecttimeout(self, timeout):
        self._connecttimeout = timeout

    @synclize
    def connect(self, address):
        host, port = address
        timer = None
        try:
            if self._connecttimeout:
                timer = Timeout(self._connecttimeout)
                timer.start()
            resolved_addrs = yield self._resolver.resolve(
                host,
                port,
                family=socket.AF_INET)
            for addr in resolved_addrs:
                family, host_port = addr
                yield self._iostream.connect(host_port)
                break
        except TimeoutException, e:
            self.close()
            raise socket.timeout(e.message)
        finally:
            if timer:
                timer.cancel()

    def sendall(self, buff):
        self._iostream.write(buff)

    def read(self, nbytes):
        if nbytes <= self._rbuffer_size:
            self._rbuffer_size -= nbytes
            return self._rbuffer.read(nbytes)

        if self._rbuffer_size > 0:
            self._iostream._read_buffer.appendleft(self._rbuffer.read())
            self._iostream._read_buffer_size += self._rbuffer_size
            self._rbuffer_size = 0

        if nbytes <= self._iostream._read_buffer_size:
            data, data_len = b''.join(
                self._iostream._read_buffer), self._iostream._read_buffer_size
            self._iostream._read_buffer.clear()
            self._iostream._read_buffer_size = 0

            if data_len == nbytes:
                return data

            self._rbuffer_size = data_len - nbytes
            self._rbuffer = StringIO(data)
            return self._rbuffer.read(nbytes)

        data = self._read(nbytes)
        if len(data) == nbytes:
            return data

        self._rbuffer_size = len(data) - nbytes
        self._rbuffer = StringIO(data)
        return self._rbuffer.read(nbytes)

    @synclize
    def _read(self, nbytes):
        timer = None
        try:
            if self._readtimeout:
                timer = Timeout(self._readtimeout)
                timer.start()
            data = yield self._iostream.read_bytes(nbytes)
            raise Return(data)
        except TimeoutException, e:
            self.close()
            raise socket.timeout(e.message)
        finally:
            if timer:
                timer.cancel()

    def recv(self, nbytes):
        return self.read(nbytes)

    def close(self):
        self._iostream.close()

    def set_nodelay(self, flag):
        self._iostream.set_nodelay(flag)

    def settimeout(self, timeout):
        pass

    def shutdown(self, direction):
        if self._iostream.fileno():
            self._iostream.fileno().shutdown(direction)

    def recv_into(self, buff):
        expected_rbytes = len(buff)
        data = self.read(expected_rbytes)
        srcarray = bytearray(data)
        nbytes = len(srcarray)
        buff[0:nbytes] = srcarray
        return nbytes

    def makefile(self, mode, other):
        return self

    def fileno(self):
        return self._iostream.fileno()


class Event(object):
    def __init__(self):
        self._waiter = []
        self._ioloop = IOLoop.current()

    def set(self):
        self._ioloop.add_callback(self._notify)

    def wait(self, timeout=None):
        current_greenlet = greenlet.getcurrent()
        self._waiter.append(current_greenlet.switch)
        waiter = Waiter()
        if timeout:
            timeout_checker = Timeout(timeout)
            timeout_checker.start(current_greenlet.throw)
            waiter.get()
            timeout_checker.cancel()
        else:
            waiter.get()

    def _notify(self):
        for waiter in self._waiter:
            waiter(self)


class Watcher(object):
    def __init__(self, fd, events):
        self._fd = fd
        self._watched_event = IOLoop.READ if events == 1 else IOLoop.WRITE
        self._value = None
        self._greenlet = greenlet.getcurrent()
        self._main = self._greenlet.parent
        self._ioloop = IOLoop.current()
        self._callback = None
        self._iohandler = None

    def start(self, callback, args):
        self._callback = callback
        self._value = args
        self._ioloop.add_handler(self._fd, self._handle_event, self._watched_event)

    def _handle_event(self, fd, events):
        self._callback(self._value)

    def stop(self):
        self._ioloop.remove_handler(self._fd)


class Pool(object):
    def __init__(self, max_size=32, wait_timeout=8, params={}):
        self._maxsize = max_size
        self._conn_params = params
        self._pool = deque(maxlen=self._maxsize)
        self._wait = deque()
        self._wait_timeout = wait_timeout
        self._count = 0
        self._started = False
        self._ioloop = IOLoop.current()
        self._event = Event()
        self._ioloop.add_future(spawn(self.start), lambda future: future)

    def create_raw_conn(self):
        pass

    def init_pool(self):
        self._count += 1
        conn = self.create_raw_conn()
        self._pool.append(conn)

    @property
    def size(self):
        return len(self._pool)

    def get_conn(self):
        while 1:
            if self._pool:
                return self._pool.popleft()
            elif self._count < self._maxsize:
                self.init_pool()
            else:
                return self.wait_conn()

    def wait_conn(self):
        timer = None
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        try:
            if self._wait_timeout:
                timer = Timeout(self._wait_timeout)
                timer.start()
            self._wait.append(child_gr.switch)
            return main.switch()
        except TimeoutException:
            raise Exception("timeout wait connections, connections size %s",
                            self.size)
        finally:
            if timer:
                timer.cancel()

    def release(self, conn):
        if self._wait:
            switch = self._wait.popleft()
            self._ioloop.add_callback(switch, conn)
        else:
            self._pool.append(conn)

    def quit(self):
        self._started = False
        self._event.set()

    def _close_all(self):
        for conn in tuple(self._pool):
            conn.close()
        self._pool = None

    def start(self):
        # self.init_pool()
        self._started = True
        self._event.wait()
        self._close_all()
