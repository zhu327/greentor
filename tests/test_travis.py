# -*- coding:utf-8 -*-
from __future__ import absolute_import
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from gtornado import green
import traceback

def test_green_sleep():
    green.sleep(1)

def test_green_task():
    return "done"

def test_call_green_task():
    result = test_green_task()
    green.sleep(1)
    return result

def test_green_timeout():
    try:
        timeout = green.Timeout(1)
        timeout.start()
        green.sleep(2)
    except green.TimeoutException:
        traceback.print_exc()        
    finally:
        timeout.cancel()

@coroutine
def test():
    yield green.spawn(test_green_task)
    yield green.spawn(test_green_sleep)
    yield green.spawn(test_call_green_task)
    yield green.spawn(test_green_timeout)


IOLoop.instance().run_sync(test)
