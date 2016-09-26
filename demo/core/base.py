# coding: utf-8

from django.db.backends.mysql.base import (SafeText, SafeBytes, six,
    DatabaseWrapper as BaseDatabaseWrapper)
from greentor.mysql import ConnectionPool

class DatabaseWrapper(BaseDatabaseWrapper):
    u"""
    支持greentor mysql connection pool 的backends
    """
    pools = {}

    def get_new_connection(self, conn_params):
        # conn = Database.connect(**conn_params)
        if not self.alias in self.pools:
            self.pools[self.alias] = ConnectionPool(
                max_size=conn_params.pop('MAX_SIZE', 32),
                keep_alive=conn_params.pop('KEEP_ALIVE', 7200),
                mysql_params=conn_params
            )
        conn = self.pools[self.alias].get_conn()
        conn.encoders[SafeText] = conn.encoders[six.text_type]
        conn.encoders[SafeBytes] = conn.encoders[bytes]
        return conn

    def _close(self):
        if self.connection is not None:
            self.pools[self.alias].release(self.connection)
