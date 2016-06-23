# coding: utf-8

from greentor import mysql
# pymysql打上异步补丁
mysql.patch_pymysql()
import pymysql
pymysql.install_as_MySQLdb()

from greentor import green
import tornado.wsgi

# 包装wsgi app运行在greenlet中，使Django admin支持异步pymysql
tornado.wsgi.WSGIContainer.__call__ = green.green(
    tornado.wsgi.WSGIContainer.__call__)

from greentor.glocal import local
from django.db.utils import ConnectionHandler as BaseConnectionHandler


class ConnectionHandler(BaseConnectionHandler):
    def __init__(self, databases=None):
        self._databases = databases
        self._connections = local()


import django.db
# 使用greenlet local替换threading local,避免threading safe问题
setattr(django.db, 'connections', ConnectionHandler())