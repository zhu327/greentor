# -*- coding:utf-8 -*-
from tornado.web import RequestHandler
from gtornado import green
# from greenlet import greenlet

class Handler(RequestHandler):
    def _execute(self, *args, **kwargs):
        orgi_execute = super(Handler, self)._execute
        return green.spawn(orgi_execute, *args, **kwargs)
