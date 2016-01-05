# -*- coding:utf-8 -*-
import sys
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.web import RequestHandler, Application
from gtornado import green

import pymysql
pymysql.install_as_MySQLdb()

from gtornado.mysql import patch_pymysql
patch_pymysql()

from gtornado.mysql import MySQLConnectionPool

params = {
        "host":"127.0.0.1", 
        "port":3306, 
        "username":"root", 
        "password":"powerall", 
        "db":"mywork"}

ConnectionPool = MySQLConnectionPool(max_size=200, mysql_params=params)


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


import test_pure_mysql
class PureHandler(RequestHandler):
    @coroutine
    def get(self):
        result = yield green.spawn(test_pure_mysql.query)
        self.write(dict(row=result))


import test_memcache
class MemCacheHandler(RequestHandler):
    @coroutine
    def get(self):
        result = yield green.spawn(test_memcache.test)
        self.write(result)

class HelloWorldHandler(RequestHandler):
    @coroutine
    def get(self):
        self.write("HelloWorld!")


app = Application([
                    (r"/async/orm/pure", PureHandler),
                    (r"/async/orm/storm", OrmTestHandler),
                    (r"/async/memcache", MemCacheHandler),
                    (r"/async/", HelloWorldHandler),
                  ])

import tornado.httpserver
http_server = tornado.httpserver.HTTPServer(app)
http_server.listen(int(sys.argv[1]))
main_ioloop = IOLoop.instance()
main_ioloop.start()
