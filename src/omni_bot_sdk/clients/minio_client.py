import asyncio
import os
from datetime import timedelta
from pathlib import Path
from threading import Lock
from typing import Optional, Tuple

from ruamel.yaml import YAML
from minio import Minio
from minio.error import S3Error


class MinioClient:
    """
    Minio 对象存储客户端。
    支持单例模式，封装了存储桶管理、文件上传、预签名URL等常用操作。
    """

    _minio_client_instance = None
    _minio_client_lock = Lock()

    def __init__(
        self,
        server: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ):
        """
        初始化Minio客户端。

        Args:
            server: Minio服务器地址
            access_key: 访问密钥
            secret_key: 密钥
            bucket: 默认使用的存储桶
            secure: 是否使用安全连接
        """
        # 单例模式初始化 Minio client
        if MinioClient._minio_client_instance is None:
            with MinioClient._minio_client_lock:
                if MinioClient._minio_client_instance is None:
                    MinioClient._minio_client_instance = Minio(
                        server,
                        access_key=access_key,
                        secret_key=secret_key,
                        secure=secure,
                    )
        self.client = MinioClient._minio_client_instance
        self.bucket = bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """
        确保存储桶存在，如果不存在则自动创建。
        """
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"创建存储桶: {self.bucket}")
        except S3Error as e:
            print(f"检查/创建存储桶时出错: {e}")
            raise

    async def wait_for_file(
        self, file_path: str, max_retries: int = 15, retry_interval: float = 2.0
    ) -> bool:
        """
        等待本地文件准备就绪（存在且非空）。

        Args:
            file_path: 文件路径
            max_retries: 最大重试次数
            retry_interval: 重试间隔(秒)

        Returns:
            bool: 文件是否就绪
        """
        path = Path(file_path)
        retries = 0

        while retries < max_retries:
            if path.exists() and path.stat().st_size > 0:
                print(f"文件已就绪: {file_path}")
                return True

            print(f"文件未就绪: {file_path}, 重试 {retries+1}/{max_retries}")
            retries += 1
            if retries < max_retries:
                await asyncio.sleep(retry_interval)

        print(f"等待文件超时: {file_path}")
        return False

    async def upload_file(
        self,
        file_path: str,
        object_name: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        异步上传文件到Minio。
        上传前会等待文件就绪。

        Args:
            file_path: 本地文件路径
            object_name: 对象名称(如果不指定则使用文件名)
            bucket_name: 存储桶名称(如果不指定则使用默认存储桶)

        Returns:
            Tuple[bool, str]: (是否成功, URL或错误信息)
        """
        try:
            file_ready = await self.wait_for_file(file_path)
            if not file_ready:
                return False, f"文件未就绪: {file_path}"

            if object_name is None:
                object_name = os.path.basename(file_path)
            bucket = bucket_name or self.bucket
            self.client.fput_object(bucket, object_name, file_path)
            url = self.client.presigned_get_object(bucket, object_name)
            print(f"文件上传成功，URL: {url}")
            return True, url
        except Exception as e:
            print(f"上传文件错误: {e}")
            return False, str(e)

    def upload_file_sync(
        self,
        file_path: str,
        object_name: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        同步上传文件到Minio。
        仅检查文件是否存在，不等待文件生成。

        Args:
            file_path: 本地文件路径
            object_name: 对象名称(如果不指定则使用文件名)
            bucket_name: 存储桶名称(如果不指定则使用默认存储桶)

        Returns:
            Tuple[bool, str]: (是否成功, URL或错误信息)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}"
            if object_name is None:
                object_name = os.path.basename(file_path)
            bucket = bucket_name or self.bucket
            self.client.fput_object(bucket, object_name, file_path)
            url = self.client.presigned_get_object(bucket, object_name)
            return True, url
        except Exception as e:
            print(f"上传文件错误: {e}")
            return False, str(e)

    def get_presigned_url(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
        expires: timedelta = timedelta(days=1),
    ) -> str:
        """
        获取文件的预签名下载URL。

        Args:
            object_name: 对象名称
            bucket_name: 存储桶名称(如果不指定则使用默认存储桶)
            expires: URL有效期

        Returns:
            str: 预签名URL
        """
        bucket = bucket_name or self.bucket
        return self.client.presigned_get_object(bucket, object_name, expires)

    def get_upload_url(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
        expires: timedelta = timedelta(days=1),
    ) -> str:
        """
        获取文件的预签名上传URL。

        Args:
            object_name: 对象名称
            bucket_name: 存储桶名称(如果不指定则使用默认存储桶)
            expires: URL有效期

        Returns:
            str: 预签名URL
        """
        bucket = bucket_name or self.bucket
        return self.client.presigned_put_object(bucket, object_name, expires)


def load_config():
    """
    加载本地config.yaml配置文件。
    """
    config_path = Path("config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return YAML().load(f)


def get_minio_client():
    """
    获取单例MinioClient实例，首次调用时从配置文件加载配置。

    Returns:
        MinioClient: 单例实例
    """
    if MinioClient._minio_client_instance is None:
        with MinioClient._minio_client_lock:
            if MinioClient._minio_client_instance is None:
                config = load_config()
                minio_config = config["minio"]
                MinioClient._minio_client_instance = MinioClient(
                    server=minio_config["server"],
                    access_key=minio_config["access_key"],
                    secret_key=minio_config["secret_key"],
                    bucket=minio_config["bucket"],
                    secure=minio_config["secure"],
                )
    return MinioClient._minio_client_instance
