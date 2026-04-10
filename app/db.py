# ABOUTME: 数据库连接和表初始化
# ABOUTME: 提供 PostgreSQL 连接上下文管理器和建表逻辑

import os
from contextlib import contextmanager
import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]


@contextmanager
def get_conn():
    with psycopg.connect(DATABASE_URL) as conn:
        yield conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS images(
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                path TEXT NOT NULL,
                thumbnail_path TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

