from __future__ import absolute_import
import sys
import time
import greenify
greenify.greenify()
import pylibmc
import random
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from gtornado import green

greenify.patch_lib("/usr/lib/x86_64-linux-gnu/libmemcached.so")

def call_mc(i):
    mc = pylibmc.Client(["localhost"])
    mc.get_stats()
    mc.disconnect_all()

@coroutine
def use_greenlet():
    s = time.time()
    yield [green.spawn(call_mc, i) for i in range(1000)]
    print(time.time() - s)

if __name__ == "__main__":
    IOLoop.instance().run_sync(use_greenlet)
