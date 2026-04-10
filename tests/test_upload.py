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
    png_bytes = _minimal_png()
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
    png_bytes = _minimal_png()
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


def _minimal_png() -> bytes:
    """生成一个 1x1 像素的最小合法 PNG 文件。

    比起从磁盘读图片，硬编码字节更可靠——测试不依赖外部文件。
    """
    import struct
    import zlib

    # PNG 文件结构：签名 + IHDR chunk + IDAT chunk + IEND chunk
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR: 宽1 高1 位深8 颜色类型2(RGB)
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = _png_chunk(b"IHDR", ihdr_data)

    # IDAT: 图像数据（1个像素，RGB 各为0，前面加 filter byte 0）
    raw = b"\x00\x00\x00\x00"
    idat = _png_chunk(b"IDAT", zlib.compress(raw))

    # IEND: 结束标记
    iend = _png_chunk(b"IEND", b"")

    return signature + ihdr + idat + iend


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """构造一个 PNG chunk：长度(4字节) + 类型(4字节) + 数据 + CRC(4字节)。"""
    import struct
    import zlib

    chunk = chunk_type + data
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
