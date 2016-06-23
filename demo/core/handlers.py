# coding: utf-8

import tornado.web
from django.db import connection


class BaseRequestHandler(tornado.web.RequestHandler):
    def on_finish(self):
        connection.close()
