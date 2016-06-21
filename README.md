## greentor

**greentor** is a fork of [gTornado](https://github.com/alex8224/gTornado)

greentor通过给pymysql打补丁,使pymysql在Tornado中的运行过程变为异步IO,相比与其它支持Tornado的mysql驱动,greentor有以下不同

1. 同步pymysql的写法
2. 理论上可以支持各种ORM的调用异步

感谢[@alex8224](https://github.com/alex8224)和他的[gTornado](https://github.com/alex8224/gTornado)

### 安装

```shell
pip install git+https://github.com/zhu327/greentor.git
```

### 使用

```python
# coding: utf-8

from greentor import green
green.enable_debug()
from greentor import mysql
mysql.patch_pymysql()
```

1. `green.enable_debug()`
  开启greenlet的调试,可以查看greenlet switch过程,非必须  
2. `mysql.patch_pymysql()`
  给pymysql打异步补丁,打上补丁后pymysql依赖于Tornado,在Tornado的IOLoop start后才能正常使用

#### 在`RequestHandler`中使用

涉及到pymysql的调用都需要运行在greenlet中,提供了3种方式实现同步代码转异步

```python
from greentor import green
from greentor import mysql
mysql.patch_pymysql()
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    @green.green
    def get(self):
        connect = MySQLdb.connect(user='root',
                                  passwd='',
                                  db='test',
                                  host='localhost',
                                  port=3306)
        cursor = connect.cursor()
        cursor.execute('SELECT * FROM app_blog LIMIT 1')
        result = cursor.fetchone()
        cursor.close()
        connect.close()
        self.finish(result[2])
```

通过`green.green`装饰器使整个get方法都运行在greenlet中,这样是最方便的使用pymysql的方式

```python
from greentor import green
from greentor import mysql
mysql.patch_pymysql()
import tornado.web
import tornado.gen

@green.green
def test_mysql():
    connect = MySQLdb.connect(user='root',
                              passwd='',
                              db='test',
                              host='localhost',
                              port=3306)
    cursor = connect.cursor()
    cursor.execute('SELECT * FROM app_blog LIMIT 1')
    result = cursor.fetchone()
    cursor.close()
    connect.close()
    return result


class MainHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        result = yield test_mysql()
        self.finish(result[2])
```

通过`green.green`装饰器包装的函数会返回`Future`对象,可以在Tornado的协程中使用

```python
from greentor import green
from greentor import mysql
mysql.patch_pymysql()
import tornado.web
import tornado.gen

def test_mysql():
    connect = MySQLdb.connect(user='root',
                              passwd='',
                              db='test',
                              host='localhost',
                              port=3306)
    cursor = connect.cursor()
    cursor.execute('SELECT * FROM app_blog LIMIT 1')
    result = cursor.fetchone()
    cursor.close()
    connect.close()
    return result


class MainHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        result = yield green.spawn(test_mysql)
        self.finish(result[2])
```

`green.spawn(callable_obj, *arg, **kwargs)`的调用与`green.green`一致

### 实例

在tests目录下有一个使用纯pymysql的实例,demo目录下有一个完整的 Tornado + Django ORM 的环境,具体可以查看demo目录下的[README](https://github.com/zhu327/greentor/tree/master/demo)