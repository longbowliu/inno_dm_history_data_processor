from minio import Minio
from minio.error import S3Error
import os
import logging
import hashlib
import pymysql
from datetime import datetime
from snowflake_id_generator import SnowflakeIDGenerator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_md5(file_path):
    """
    计算文件的 MD5 值

    :param file_path: 文件路径
    :return: MD5 值（字符串）
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def upload_file_to_minio(minio_server, access_key, secret_key, bucket_name, object_name, file_path, secure=False, chunk_size=64 * 1024 * 1024):
    """
    上传文件到 MinIO 服务器

    :param minio_server: MinIO 服务器地址
    :param access_key: 访问密钥
    :param secret_key: 秘密密钥
    :param bucket_name: 存储桶名称
    :param object_name: 对象名称（上传后的文件名）
    :param file_path: 本地文件路径
    :param secure: 是否使用 HTTPS
    :param chunk_size: 分块大小（默认 64MB）
    :return: None
    """
    # 检查本地文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"本地文件不存在: {file_path}")
        return

    # 计算文件的 MD5 值
    file_md5 = calculate_md5(file_path)
    logger.info(f"文件 MD5 值: {file_md5}")

    # 创建 MinIO 客户端
    client = Minio(
        minio_server,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure
    )

    try:
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        # 分块上传
        with open(file_path, "rb") as file_data:
            client.put_object(bucket_name, object_name, file_data, file_size, part_size=chunk_size)
        logger.info(f"文件上传成功: {object_name} 到存储桶 {bucket_name}")
        
        # 插入数据库
        connection = None
        try:
            connection = pymysql.connect(
                host="172.16.210.98",
                port=3308,
                user="root",
                password="root",
                database="data_management_20250612"
            )
            
            with connection.cursor() as cursor:
                # 提取文件名和扩展名
                file_name = os.path.basename(file_path)
                extension_name = os.path.splitext(file_name)[1][1:] if os.path.splitext(file_name)[1] else ""
                unique_id = id_generator.generate_id()
                # 插入数据
                sql = """
                INSERT INTO dm_attach (
                    id, file_name, bucket_name, object_name, md5, extension_name, create_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    unique_id,
                    file_name,
                    bucket_name,
                    object_name,
                    file_md5,
                    extension_name,
                    datetime.now()
                ))
                connection.commit()
                logger.info(f"数据插入成功: {file_name}")
        except Exception as e:
            logger.error(f"数据库插入失败: {e}")
            return
        finally:
            if connection:
                connection.close()
    except S3Error as e:
        logger.error(f"上传失败: {e}")
    except Exception as e:
        logger.error(f"发生未知错误: {e}")

# 示例用法
if __name__ == "__main__":
    id_generator = SnowflakeIDGenerator(worker_id=1)
    upload_file_to_minio(
        minio_server="localhost:9000",
        access_key="LjpIoEnrisuMBq6T",
        secret_key="HZ9iClAqIgbPg71nZGKr48oiDO4TtCPc",
        bucket_name="inno-pc",
        object_name="C-B23-E-1-FK-DFT-12.inno_pc",
        file_path="/home/demo/C-B23-E-1-FK-DFT-12.inno_pc"
    )