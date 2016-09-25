# coding: utf-8

import tornado.web
from django.db import connections


class BaseRequestHandler(tornado.web.RequestHandler):
    def on_finish(self):
        connections.close_all()
