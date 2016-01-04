# -*- coding:utf-8 -*-
class Singleton(type):
    def __call__(clazz, *args, **kwargs):
        if hasattr(clazz, "_instance"):
            return clazz._instance
        else:
            clazz._instance = super(Singleton, clazz).__call__(*args, **kwargs)
            return clazz._instance
