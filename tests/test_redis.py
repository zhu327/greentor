from gtornado.redis import RedisConnectionPool
from gtornado import green
from redis import StrictRedis
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, asynchronous
from tornado.gen import coroutine

#green.enable_debug()
pool = RedisConnectionPool()

class SubHandler(RequestHandler):

    def listen(self, channel):
        print("listen pub for channel %s" % channel)
        client = StrictRedis(host="localhost", db=0, connection_pool=pool)
        pubsub = client.pubsub()
        pubsub.subscribe(channel)
        for item in pubsub.listen():
            data = item["data"]
            if data != 1L:
                return data

    @coroutine
    def get(self):
        channel = self.get_argument("channel", "inbox")
        message = yield green.spawn(self.listen, channel)
        self.write(message)


def redis_test(i):
    client = StrictRedis(host="localhost", db=0, connection_pool=pool)
    client.set("name_i" + str(i+1), "alex" + str(i))
    client.get("name")

def sleep():
    green.sleep(10)

@coroutine
def start():
    result = yield [green.spawn(redis_test, i) for i in range(2)]
    #yield green.spawn(sleep)
    print("done")

app = Application([
                    (r"/sub", SubHandler),
                    ])

app.listen(30001)


#IOLoop.current().run_sync(start)    
IOLoop.instance().start()
