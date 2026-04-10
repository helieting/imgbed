import uuid
from contextlib import asynccontextmanager
from pathlib import Path


from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse


from app.db import get_conn, init_db

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


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
    dest.write_bytes(await file.read())

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO images (id, filename, content_type, path) "
            "VALUES (%s, %s, %s, %s)",
            (image_id, file.filename, file.content_type, str(dest)),
        )
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


