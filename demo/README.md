## Tornado + Django ORM

***

这是一个 Tornado + Django ORM 运行环境的demo,demo目录是Django的配置文件目录,app目录是Django的app

不同与Django app目录下的views.py,我将其重命名为handlers.py,是Tornado的RequestHanlder的集合

### 运行

```shell
python application.py
```

在运行tornado的同时,Django admin也是可以访问的

### 说明

```python
import tornado.web
import tornado.gen
from greentor import green

from .models import Blog


class BlogHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        blogs = yield green.spawn(Blog.objects.all)
        self.write(blogs)
```

这样使用是会报错的,因为返回的blogs是QuerySet对象是Lazy的,需要调用**_fetch_all**方法才执行了SQL查询

### 扩展

在Tornado中使用Django session user和Django request对象也是可行的,可以参考:

<https://gist.github.com/bdarnell/654157>

当然需要查询数据库的地方都要加上`green.green`装饰器