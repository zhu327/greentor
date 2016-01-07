from gtornado.redis import RedisConnectionPool
from gtornado import green
from redis import StrictRedis
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application
from tornado.gen import coroutine

#green.enable_debug()
pool = RedisConnectionPool(host="localhost", port=18000, db=0)

class SubHandler(RequestHandler):

    def listen(self, channel):
        print("listen pub for channel %s" % channel)
        client = StrictRedis(connection_pool=pool)
        pubsub = client.pubsub()
        pubsub.subscribe(channel)
        for item in pubsub.listen():
            data = item["data"]
            if data != 1L:
                return data

    @coroutine
    def get(self):
        channel = self.get_argument("channel", "inbox")
        message = yield green.spawn(self.listen, channel, timeout=10)
        self.write(message)


class IfBlockingHandler(RequestHandler):
    @coroutine
    def get(self):
        self.write("no blocking")


class RedisTest(RequestHandler):
    def get_value(self):
        client = StrictRedis(connection_pool=pool)
        return client.get("name")

    @coroutine
    def get(self):
        name = yield green.spawn(self.get_value)
        self.write(name)

def redis_test(i):
    client = StrictRedis(host="localhost", db=0, connection_pool=pool)
    client.set("name_i" + str(i+1), "alex" + str(i))
    client.get("name")

def sleep():
    green.sleep(10)


app = Application([
                    (r"/sub", SubHandler),
                    (r"/name", RedisTest),
                    (r"/ifblocking", IfBlockingHandler),
                    ])

app.listen(30001)


#IOLoop.current().run_sync(start)    
IOLoop.instance().start()
