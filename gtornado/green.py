# -*- coding:utf-8 -*-
from __future__ import absolute_import
import sys
import socket
import time
import greenlet
from functools import wraps

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.concurrent import Future
from tornado.gen import coroutine, Return
from tornado.netutil import Resolver


IS_PYPY = False
try:
    import __pypy__
    __pypy__
    IS_PYPY = True
except:
    pass

def set_resolver(resolver):
    Resolver.configure(resolver)

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
                buff.append(trace_line % (srcfile, lineno, func_name, "".join(codesample)))

            print("".join(buff))
     
    greenlet.settrace(trace_green)    


__all__ = ("IS_PYPY", "spawn", "AsyncSocket", "GreenTask", "synclize", 
            "Waiter", "sleep", "Timeout", "Event", "Watcher", "Pool")


class Hub(object):
    def __init__(self):
        self._greenlet = greenlet.getcurrent()
        self._ioloop = IOLoop.current()

    @property
    def greenlet(self):
        return self._greenlet

    def switch(self):
        self._greenlet.switch()

    @property
    def ioloop(self):
        return self._ioloop

    def run_later(self, deadline, callback, *args, **kwargs):
        return self.ioloop.add_timeout(time.time() + deadline, 
                                      callback, *args, **kwargs)

    def run_callback(self, callback, *args, **kwargs):
        self.ioloop.add_callback(callback, *args, **kwargs)
            

hub = Hub()

def get_hub():
    return hub


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


class TimeoutException(Exception): pass


class Timeout(object):
    def __init__(self, deadline, ex=TimeoutException):
        self._greenlet = greenlet.getcurrent()
        self._ex = ex
        self._callback = None
        self._deadline = deadline
        self._delta = time.time() + deadline
        self._ioloop = IOLoop.current()

    def start(self, callback=None):
        errmsg = "%s timeout, deadline is %d seconds" % (
                str(self._greenlet), self._deadline)
        if callback:
            self._callback = self._ioloop.add_timeout(self._delta, 
                                                      callback,
                                                      self._ex(errmsg))
        else:
            self._callback = self._ioloop.add_timeout(self._delta, 
                                                      self._greenlet.throw,
                                                      self._ex(errmsg))

    def cancel(self):
        assert self._callback, "Timeout not started"
        self._ioloop.remove_timeout(self._callback)
        self._greenlet = None


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


class AsyncSocket(object):
    def __init__(self, sock):
        self._iostream = IOStream(sock)
        self._resolver = Resolver()
        self._readtimeout = 0
        self._connecttimeout = 0
   
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
            resolved_addrs = yield self._resolver.resolve(host, port, family=socket.AF_INET)
            for addr in resolved_addrs:
                family, host_port = addr
                yield self._iostream.connect(host_port)
                break
        except TimeoutException:
            self.close()
            raise
        finally:
            if timer:
                timer.cancel()

    #@synclize
    def sendall(self, buff):
        self._iostream.write(buff)

    @synclize
    def read(self, nbytes, partial=False):
        timer = None
        try:
            if self._readtimeout:
                timer = Timeout(self._readtimeout)
                timer.start()
            buff = yield self._iostream.read_bytes(nbytes, partial=partial)
            raise Return(buff)
        except TimeoutException:
            self.close()
            raise
        finally:
            if timer:
                timer.cancel()

    def recv(self, nbytes):
        return self.read(nbytes, partial=True)

    @synclize
    def readline(self, max_bytes=-1):
        timer = None
        if self._readtimeout:
            timer = Timeout(self._readtimeout)
            timer.start()
        try:
            if max_bytes > 0:
                buff = yield self._iostream.read_until('\n', max_bytes=max_bytes)
            else:
                buff = yield self._iostream.read_until('\n')
            raise Return(buff)
        except TimeoutException:
            self.close()
            raise
        finally:
            if timer:
                timer.cancel()

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
        data = self.read(expected_rbytes, True)
        srcarray = bytearray(data)
        nbytes = len(srcarray)
        buff[0:nbytes] = srcarray
        return nbytes

    def makefile(self, mode, other):
        return self


class Pool(object):
    def __init__(self, max_size=-1, params={}):
        self._maxsize = max_size
        self._conn_params = params
        self._pool = []
        self._started = False
        self._ioloop = IOLoop.current()
        self._event = Event()
        self._ioloop.add_future(
                                spawn(self.start), 
                                lambda future: future)

    def create_raw_conn(self):
        pass

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

    def release(self, conn):
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
