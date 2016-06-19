# coding: utf-8

from greentor import green
green.enable_debug()
from greentor import mysql
mysql.patch_pymysql()

import pymysql
pymysql.install_as_MySQLdb()

import MySQLdb

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.gen

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class MainHandler(tornado.web.RequestHandler):
    @green.green
    def get(self):
        connect = MySQLdb.connect(user='root',
                                  passwd='',
                                  db='blog',
                                  host='localhost',
                                  port=3306)
        cursor = connect.cursor()
        cursor.execute('SELECT * FROM blogs LIMIT 1')
        result = cursor.fetchone()
        cursor.close()
        connect.close()
        self.write(str(result))


def main():
    tornado.options.parse_command_line()
    application = tornado.web.Application([(r"/", MainHandler), ], debug=True)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
