# ABOUTME: S3 兼容对象存储的上传和下载操作
# ABOUTME: 支持 Tigris, Cloudflare R2 等S3 兼容服务



import os
import aioboto3


BUCKET_NAME = os.environ.get("BUCKET_NAME", "imgbed-uploads")
ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL_S3")

session = aioboto3.Session()


def _client():
    """创建 S3 client。如果设了 endpoint URL 就用它（MinIO、Tigris），否则用 AWS 默认。"""
    return session.client("s3", endpoint_url=ENDPOINT_URL)


async def upload(key: str, data: bytes, content_type: str) -> None:
    async with _client() as s3:
        await s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=data, ContentType=content_type)


async def download(key: str) -> bytes:
    async with _client() as s3:
        resp = await s3.get_object(Bucket=BUCKET_NAME, Key=key)
        return await resp["Body"].read()