# ABOUTME: arq 异步任务定义，处理缩略图生成
# ABOUTME: 由 arq worker 进程消费 Redis 队列中的任务

import os
import io

from arq.connections import RedisSettings
from PIL import Image

from app.db import get_conn
import app.storage as storage


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


    key = row[0]
    data = await storage.download(key)
    img = Image.open(io.BytesIO(data))

    img.thumbnail(THUMB_MAX_SIZE)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    thumb_bytes = buf.getvalue()

    thumb_key = f"thumbnails/{key}"
    await storage.upload(thumb_key, thumb_bytes, "image/png")

    with get_conn() as conn:
        conn.execute(
            "UPDATE images SET thumbnail_path = %s WHERE id = %s",
            (thumb_key, image_id),
        )


class WorkerSettings:
    """arq worker 的配置。arq 启动时会读取这个类。

    - functions: worker 能执行哪些任务
    - redis_settings: 连哪个 Redis
    """

    functions = [generate_thumbnail]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
