# coding: utf-8

import tornado.web
from greentor import green

from core.handlers import BaseRequestHandler
from .models import Blog


class HelloHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Hello, world ! \n')


class BlogHandler(BaseRequestHandler):
    @green.green
    def get(self):
        blog = Blog.objects.first()
        self.finish(blog.content)
