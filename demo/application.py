#!/usr/bin/env python
# coding: utf-8

from greentor import green
from greentor import mysql
# pymysql打上异步补丁
mysql.patch_pymysql()
import pymysql
pymysql.install_as_MySQLdb()

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

from tornado.options import options, define, parse_command_line
import django.core.handlers.wsgi
import tornado.httpserver
import tornado.ioloop
import tornado.wsgi
import tornado.web

# 包装wsgi app运行在greenlet中，使Django admin支持异步pymysql
tornado.wsgi.WSGIContainer.__call__ = green.green(
    tornado.wsgi.WSGIContainer.__call__)

django.setup()

from django.conf import settings

import app.urls

define('port', type=int, default=8000)

tornado_settings = {'debug': settings.DEBUG}


def main():
    parse_command_line()

    wsgi_app = tornado.wsgi.WSGIContainer(
        django.core.handlers.wsgi.WSGIHandler())

    urls = app.urls.urls + [('.*', tornado.web.FallbackHandler, dict(
        fallback=wsgi_app)), ]

    tornado_app = tornado.web.Application(urls, **tornado_settings)
    server = tornado.httpserver.HTTPServer(tornado_app)
    server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
