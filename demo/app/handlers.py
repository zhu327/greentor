# coding: utf-8

import tornado.web

from core.handlers import BaseRequestHandler
from .models import Blog


class HelloHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Hello, world ! \n')


class BlogHandler(BaseRequestHandler):
    def get(self):
        blog = Blog.objects.first()
        self.finish(blog.content)
