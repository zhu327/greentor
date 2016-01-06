from __future__ import absolute_import
import sys
import time
import greenify
greenify.greenify()
import pylibmc
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.web import RequestHandler, Application
from gtornado import green

greenify.patch_lib("/usr/lib/x86_64-linux-gnu/libmemcached.so")

class MCPool(green.Pool):
    def create_raw_conn(self):
        return pylibmc.Client(["localhost"])
    
mcpool = MCPool(200)

def call_mc(i):
    try:
        mc = mcpool.get_conn()
        mc.set("timestamp", str(time.time()))
        return mc.get_stats()
    finally:
        mcpool.release(mc)

class Hello(RequestHandler):
    @coroutine
    def get(self):
        result = yield green.spawn(call_mc, 1) 
        self.write(dict(rows=result))

if __name__ == "__main__":
    app = Application([(r"/async/memcache", Hello)])
    app.listen(int(sys.argv[1]))
    IOLoop.instance().start()
