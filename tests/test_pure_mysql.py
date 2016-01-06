# -*- coding:utf-8 -*-
from gtornado.mysql import MySQLConnectionPool

ConnectionPool = MySQLConnectionPool()
columns = ("id", "phone", "home", "office")

def query():
    connection = None
    try:
        connection = ConnectionPool.get_conn()     
        with connection.cursor() as cursor:
            sql = "select * from address_book"
            cursor.execute(sql)
            rs = []
            while 1:
                result = cursor.fetchmany()
                if result:
                    row = dict(zip(columns, result[0]))
                    rs.append(row)
                else:
                    break
            return rs
    except Exception as ex:
        print(ex)
        raise
    finally:
        if connection:
            ConnectionPool.release(connection)
