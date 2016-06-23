#!/usr/bin/env python
# coding: utf-8

import monkey_patch

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")
import django
django.setup()

from tornado.options import options, define, parse_command_line
import tornado.httpserver
import tornado.ioloop
import tornado.wsgi
import tornado.web

import django.core.handlers.wsgi
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
