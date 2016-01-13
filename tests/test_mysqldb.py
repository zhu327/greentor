# -*- coding:utf-8 -*-
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application
from tornado.gen import coroutine
from gtornado import green

import MySQLdb.constants
import MySQLdb.converters
import MySQLdb.cursors

import greenify
greenify.greenify()

# green.enable_debug()
assert greenify.patch_lib("/usr/lib/x86_64-linux-gnu/libmysqlclient.so")
conn_params = {
                "host": "10.86.11.116", "port":3306, 
                "user": "root", "passwd": "123456",
                "db": "mywork", "charset": "utf8"
                }

def test_select():
    db = None
    try:
        db = MySQLdb.connect(**conn_params)
        db.autocommit(True)
        cursor = db.cursor()
        cursor.execute("select * from address_book")
        while True:
            result = cursor.fetchmany()
            if result:
                pass
            else:
               break
        cursor.close()    
    except:
        raise
    finally:
        if db:
            db.close

def test_concurrent_wait():
    db = None
    try:
        db = MySQLdb.connect(**conn_params)
        cursor = db.cursor()
        cursor.execute("select sleep(1)")
        print("done")
        cursor.close()
    except:
        raise
    finally:
        if db:
            db.close()

@coroutine
def start():
    yield [green.spawn(test_concurrent_wait) for _ in range(1000)]
    #yield [green.spawn(test_select) for _ in range(100)]
    import  time
    time.sleep(10)

class DbHandler(RequestHandler):
    @coroutine
    def get(self):
        yield green.spawn(test_select)
        self.write(file("/home/alex/index").read())

app = Application([(r"/", DbHandler)])
app.listen(30001)
#IOLoop.instance().run_sync(start)
IOLoop.instance().start()
