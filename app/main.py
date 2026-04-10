# ABOUTME: 图床服务的 HTTP 端点，处理图片上传、获取和缩略图
# ABOUTME: 使用 FastAPI 框架，图片元数据存 PostgreSQL

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.db import get_conn, init_db

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # 创�� arq 的 Redis 连接池，存在 app.state 上供端点使用
    app.state.arq = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    yield
    await app.state.arq.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "only images allowed")
    
    image_id = uuid.uuid4().hex[:10]
    suffix = Path(file.filename or "").suffix
    dest = UPLOAD_DIR / f"{image_id}{suffix}"
    content = await file.read()
    dest.write_bytes(content)

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO images (id, filename, content_type, path) "
            "VALUES (%s, %s, %s, %s)",
            (image_id, file.filename, file.content_type, str(dest)),
        )
    # 往队列塞任务，worker 会异步生成缩略图
    await app.state.arq.enqueue_job("generate_thumbnail", image_id=image_id)

    return {"id": image_id, "url": f"/i/{image_id}"}

@app.get("/i/{image_id}")
def get_image(image_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT path, content_type FROM images WHERE id = %s",
            (image_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404)
    path, content_type = row
    return FileResponse(path, media_type=content_type)


@app.get("/i/{image_id}/thumbnail")
def get_thumbnail(image_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT thumbnail_path, content_type FROM images WHERE id = %s",
            (image_id,),
        ).fetchone()
    if not row or not row[0]:
        raise HTTPException(404)
    path, content_type = row
    return FileResponse(path, media_type=content_type)


