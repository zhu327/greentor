# -*- coding:utf-8 -*-
from tornado.ioloop import IOLoop
from tornado.web import Application
from gtornado import Handler
import MySQLdb.constants
import MySQLdb.converters
import MySQLdb.cursors
from storm.locals import *

import greenify
greenify.greenify()

# green.enable_debug()
assert greenify.patch_lib("/usr/lib/x86_64-linux-gnu/libmysqlclient.so")

conn_params = {
                "host": "10.86.11.116", "port":3306, 
                "user": "root", "passwd": "123456",
                "db": "mywork", "charset": "utf8"
                }



columns = ("id", "phone", "home", "office")

class AddressBook(object):
    __storm_table__ = "address_book"

    id = Int(primary=True)
    home = Unicode()
    phone = Unicode()
    office = Unicode()


class TestHandler(Handler):

    def test_select(self):
        db = None
        try:
            db = MySQLdb.connect(**conn_params)
            db.autocommit(True)
            cursor = db.cursor()
            cursor.execute("select * from address_book")
            while True:
                result = cursor.fetchmany()
                if result:
                    if result:
                        yield dict(zip(columns, result[0]))
                else:
                   break
            cursor.close()    
        except:
            raise
        finally:
            if db:
                db.close

    def prepare(self):
        self.db = None
        uri = "mysql://root:123456@10.86.11.116/mywork"
        database = create_database(uri)
        self.db = Store(database)

    def get(self):
        # for row in self.test_select():
            # print(row)
        addrbooks = self.db.find(AddressBook, AddressBook.phone==u'13800138000')
        for addrbook in addrbooks:
            print(addrbook.home)
        self.write("ok")

    def finish(self, chunk=None):
        if self.db:
            self.db.close()
        super(TestHandler, self).finish(chunk)

app = Application([(r"/", TestHandler)])
app.listen(30001)
IOLoop.instance().start()
