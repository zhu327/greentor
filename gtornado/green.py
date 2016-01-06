# -*- coding:utf-8 -*-
from __future__ import absolute_import
import sys
import time
import socket
import greenlet
from functools import wraps

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.concurrent import Future
from tornado.gen import coroutine, Return

IS_PYPY = False
try:
    import __pypy__
    __pypy__
    IS_PYPY = True
except:
    pass

if not IS_PYPY:
    def enable_debug():
        def trace(event, args):
            print(event, args)
        greenlet.settrace(trace)    

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
    #将当前fd以events注册到ioloop中，当事件发生时，调用回调函数唤醒watcher
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
    
    @synclize
    def connect(self, address):
        yield self._iostream.connect(address)

    #@synclize
    def sendall(self, buff):
        self._iostream.write(buff)

    @synclize
    def read(self, nbytes, partial=False):
        buff = yield self._iostream.read_bytes(nbytes, partial=partial)
        raise Return(buff)

    def close(self):
        self._iostream.close()

    def set_nodelay(self, flag):
        self._iostream.set_nodelay(flag)


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
