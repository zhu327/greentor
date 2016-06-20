# coding: utf-8

import tornado.web
from greentor import green

from .models import Blog


class HelloHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Hello, world ! \n')


class BlogHandler(tornado.web.RequestHandler):
    @green.green
    def get(self):
        blog = Blog.objects.first()
        self.write(blog.content)