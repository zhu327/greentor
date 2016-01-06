# -*- coding:utf-8 -*-
from storm.locals import *

class AddressBook(object):
    __storm_table__ = "address_book"

    id = Int(primary=True)
    home = Unicode()
    phone = Unicode()
    office = Unicode()

class StormStore(object):
    def __init__(self):
        self._store = None

    def __enter__(self):
        uri = "mysql://root:powerall@10.86.11.116/mywork"
        database = create_database(uri)
        self._store = Store(database)
        return self._store

    def __exit__(self, a, b, c):
        if self._store:
            self._store.close()


class AddressBookDao(object):

    @staticmethod
    def query_by_phone(phone):
        with StormStore() as store:
            addr_book = store.find(AddressBook, AddressBook.phone==phone).one()
            addressbook = {}
            addressbook["id"] = addr_book.id
            addressbook["phone"] = addr_book.phone
            addressbook["home"] = addr_book.home
            addressbook["office"] = addr_book.office
            return addressbook
