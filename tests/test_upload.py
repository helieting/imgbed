# ABOUTME: 图片上传和获取的集成测试
# ABOUTME: 打真实 PostgreSQL，不 mock 任何东西

import pytest


@pytest.mark.anyio
async def test_health(client):
    """最简单的测试：健康检查端点返回 200。"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_upload_image(client):
    """上传一张图片，验证返回 id 和 url。"""
    # 构造一个假的 PNG 文件（1x1 像素的最小 PNG）
    # files 参数模拟浏览器的 multipart 表单上传
    png_bytes = _make_png()
    resp = await client.post(
        "/upload",
        files={"file": ("test.png", png_bytes, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "url" in data
    assert data["url"].startswith("/i/")


@pytest.mark.anyio
async def test_upload_rejects_non_image(client):
    """上传非图片文件，应该返回 400。"""
    resp = await client.post(
        "/upload",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_image(client):
    """上传后用返回的 url 获取图片，验证内容一致。"""
    png_bytes = _make_png()
    upload_resp = await client.post(
        "/upload",
        files={"file": ("test.png", png_bytes, "image/png")},
    )
    url = upload_resp.json()["url"]

    get_resp = await client.get(url)
    assert get_resp.status_code == 200
    assert get_resp.headers["content-type"] == "image/png"
    assert get_resp.content == png_bytes


@pytest.mark.anyio
async def test_get_image_not_found(client):
    """访问不存在的图片 id，应该返回 404。"""
    resp = await client.get("/i/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_upload_does_not_return_thumbnail_url(client):
    """上传图片后，返回里不包含 thumbnail_url（缩略图异步生成）。"""
    png_bytes = _make_png(800, 600)
    resp = await client.post(
        "/upload",
        files={"file": ("big.png", png_bytes, "image/png")},
    )
    data = resp.json()
    assert "thumbnail_url" not in data


@pytest.mark.anyio
async def test_thumbnail_not_ready_before_worker(client):
    """worker 处理前，缩略图端点返回 404。"""
    png_bytes = _make_png(800, 600)
    resp = await client.post(
        "/upload",
        files={"file": ("big.png", png_bytes, "image/png")},
    )
    image_id = resp.json()["id"]

    thumb_resp = await client.get(f"/i/{image_id}/thumbnail")
    assert thumb_resp.status_code == 404


@pytest.mark.anyio
async def test_thumbnail_available_after_worker(client):
    """直接调用任务函数后，缩略图可正常获取且尺寸正确。"""
    import io

    from PIL import Image

    from app.worker import generate_thumbnail

    # 上传一张 800x600 的图
    png_bytes = _make_png(800, 600)
    resp = await client.post(
        "/upload",
        files={"file": ("big.png", png_bytes, "image/png")},
    )
    image_id = resp.json()["id"]

    # 模拟 worker：直接调用任务函数，ctx 传空字典即可
    await generate_thumbnail({}, image_id=image_id)

    # 现在缩略图应该可以获取了
    thumb_resp = await client.get(f"/i/{image_id}/thumbnail")
    assert thumb_resp.status_code == 200

    thumb = Image.open(io.BytesIO(thumb_resp.content))
    assert thumb.width <= 200
    assert thumb.height <= 200
    assert thumb.size == (200, 150)


def _make_png(width: int = 1, height: int = 1) -> bytes:
    """用 Pillow 生成指定尺寸的纯色 PNG。

    比手动拼字节更灵活，可以指定任意尺寸来测试缩略图。
    """
    import io

    from PIL import Image

    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
