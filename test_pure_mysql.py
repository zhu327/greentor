# -*- coding:utf-8 -*-
from gtornado.mysql import ConnectionPool

columns = ("id", "name", "grade_id", "status", "createuser", "createtime")

def query():
    connection = None
    try:
        connection = ConnectionPool.get_conn()     
        with connection.cursor() as cursor:
            sql = "select * from banji"
            cursor.execute(sql)
            rs = []
            while 1:
                result = cursor.fetchmany()
                if result:
                    row = result[0]
                    row = dict(zip(columns, row))
                    row["createtime"] = str(row["createtime"])
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
