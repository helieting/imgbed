# ABOUTME: 测试的共享配置，提供 httpx 异步客户端和测试后清理
# ABOUTME: pytest 自动加载此文件，里面的 fixture 对所有测试可用

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_conn, init_db
from app.main import app


@pytest.fixture
async def client():
    """提供一个 httpx 异步客户端，直接连接 FastAPI app。

    关键概念：
    - ASGITransport: 让 httpx 直接调用 FastAPI，不需要启动真实服务器
    - base_url: 随便填一个，因为请求不会真的走网络
    - async with: 确保客户端用完后正确关闭
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db():
    """每个测试前确保表存在，测试后清空数据。

    关键概念：
    - autouse=True: 不需要显式传入，每个测试自动使用
    - yield 前面是 setup（测试前），yield 后面是 teardown（测试后）
    """
    init_db()
    yield
    with get_conn() as conn:
        conn.execute("DELETE FROM images")
