# -*- coding:utf-8 -*-
from gtornado.memcache import MemCachePool

memcache_pool = MemCachePool(200)

def test():
    client = None
    try:
        client = memcache_pool.get_conn()
        client.set("info", {"name":"alex", "address":"shenzhen"})
        return client.get("info")
    except:
        raise
    finally:
        if client:
            memcache_pool.release(client)
