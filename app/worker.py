# ABOUTME: arq 异步任务定义，处理缩略图生成
# ABOUTME: 由 arq worker 进程消费 Redis 队列中的任务

import os
from pathlib import Path

from arq.connections import RedisSettings
from PIL import Image

from app.db import get_conn

UPLOAD_DIR = Path("uploads")
THUMB_DIR = UPLOAD_DIR / "thumbnails"
THUMB_DIR.mkdir(parents=True, exist_ok=True)

THUMB_MAX_SIZE = (200, 200)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


async def generate_thumbnail(ctx: dict, *, image_id: str) -> None:
    """从数据库读取图片路径，生成缩略图，更新数据库。

    arq 调用时：第一个参数 ctx 是 arq 的上下文，image_id 作为关键字参数传入。
    """

    with get_conn() as conn:
        row = conn.execute(
            "SELECT path, content_type FROM images WHERE id = %s",
            (image_id,),
        ).fetchone()

    if not row:
        return

    path = row[0]
    img = Image.open(path)
    img.thumbnail(THUMB_MAX_SIZE)

    thumb_path = THUMB_DIR / Path(path).name
    img.save(thumb_path)

    with get_conn() as conn:
        conn.execute(
            "UPDATE images SET thumbnail_path = %s WHERE id = %s",
            (str(thumb_path), image_id),
        )


class WorkerSettings:
    """arq worker 的配置。arq 启动时会读取这个类。

    - functions: worker 能执行哪些任务
    - redis_settings: 连哪个 Redis
    """

    functions = [generate_thumbnail]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
