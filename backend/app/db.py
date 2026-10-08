from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from .config import settings


@contextmanager
def connection():
    s = settings()
    with psycopg.connect(host=s.db_host, dbname=s.db_name, user=s.db_user,
                         password=s.db_password.get_secret_value(), connect_timeout=5,
                         options='-c statement_timeout=5000', row_factory=dict_row) as conn:
        yield conn
