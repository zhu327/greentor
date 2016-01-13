# -*- coding:utf-8 -*-
import sys
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.web import RequestHandler, Application
from gtornado import green
import requests
from gtornado.requests import patch_requests
patch_requests()

green.set_resolver("tornado.platform.caresresolver.CaresResolver")

class HelloWorldHandler(RequestHandler):
    def get_url(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"}
        return requests.get(url, headers=headers)

    @coroutine
    def get(self):
        response = yield green.spawn(self.get_url, "http://www.163.com")
        self.write(response.text)


class IfBlockingHandler(RequestHandler):
    def get(self):
        self.write("always serving")


app = Application([
                    (r"/", HelloWorldHandler),
                    (r"/ifblocking", IfBlockingHandler),
                  ])

app.listen(int(sys.argv[1]))
IOLoop.instance().start()
