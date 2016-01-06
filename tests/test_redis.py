from gtornado.redis import RedisConnectionPool
from gtornado import green
from redis import StrictRedis
from tornado.ioloop import IOLoop
from tornado.gen import coroutine 

#green.enable_debug()

pool = RedisConnectionPool()

def redis_test(i):
    print(i)
    client = StrictRedis(host="localhost", db=0)
    client.set("name_i" + str(i+1), "alex" + str(i))
    client.get("name")

def sleep():
    green.sleep(10)

@coroutine
def start():
    result = yield [green.spawn(redis_test, i) for i in range(1000)]
    yield green.spawn(sleep)
    print("done")


IOLoop.current().run_sync(start)    
