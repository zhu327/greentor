# coding: utf-8

from handlers import HelloHandler, BlogHandler

urls=[
    (r"/", HelloHandler),
    (r"/blog/", BlogHandler),
]