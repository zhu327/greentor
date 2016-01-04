# -*- coding:utf-8 -*-
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.web import RequestHandler, Application
import green
import pymysql
pymysql.install_as_MySQLdb()
from gtornado.mysql import patch_pymysql
patch_pymysql()
from gtornado.test_pure_mysql import query
import sys
# import greenlet

# def trace_green(event, args):
    # print(event, args)
    # return


# greenlet.settrace(trace_green)


import orm_storm
def query_by_phone():
    phone = u"13800138000"
    addrbook = orm_storm.AddressBookDao()
    addr_book = addrbook.query_by_phone(phone)
    addressbook = {}
    addressbook["id"] = addr_book.id
    addressbook["phone"] = addr_book.phone
    addressbook["home"] = addr_book.home
    addressbook["office"] = addr_book.office
    return addressbook


class OrmTestHandler(RequestHandler):
    @coroutine
    def get(self):
        result = yield green.spawn(query_by_phone)
        self.write(dict(rows=result))

class PureHandler(RequestHandler):
    @coroutine
    def get(self):
        result = yield green.spawn(query)
        self.write(dict(row=result))

import orm_sqlalchemy
class OrmSqlHandler(RequestHandler):
    @coroutine
    def get(self):
        result = yield green.spawn(orm_sqlalchemy.test)
        self.write(dict(rows=result))


import test_memcache
class MemCacheHandler(RequestHandler):
    @coroutine
    def get(self):
        result = yield green.spawn(test_memcache.test)
        self.write(result)

app = Application([
                    (r"/async/orm/pure", PureHandler),
                    (r"/async/orm/storm", OrmTestHandler),
                    (r"/async/orm/sqlalchemy", OrmSqlHandler),
                    (r"/async/memcache", MemCacheHandler),
                  ])

import tornado.httpserver
http_server = tornado.httpserver.HTTPServer(app)
http_server.listen(int(sys.argv[1]))
main_ioloop = IOLoop.instance()
main_ioloop.start()
