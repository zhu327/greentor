# coding: utf-8

import tornado.web
from django.db import connections
from greentor import green


class BaseRequestHandler(tornado.web.RequestHandler):
    def on_finish(self):
        connections.close_all()

    @green.green
    def _execute(self, *args, **kwargs):
        return super(BaseRequestHandler, self)._execute(*args, **kwargs)
