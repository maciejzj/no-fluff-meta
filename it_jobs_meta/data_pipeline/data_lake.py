"""Raw data storage for job offer postings scrapped from the web."""

from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path

import boto3
import redis

from it_jobs_meta.common.utils import load_yaml_as_dict


class DataLake(ABC):
    """Key-value object storage interface for raw data scraped data."""

    @abstractmethod
    def set_data(self, key: str, data: str):
        """Store data under key.

        Data is assumed to be a JSON string.
        """

    @abstractmethod
    def get_data(self, key: str) -> str:
        """Get data stored under key.

        Data is assumed ot be a JSON string.
        """


class RedisDataLake(DataLake):
    """Redis-based key-value storage made for development and prototyping."""

    def __init__(self, password: str, host_address: str, db_num: int):
        self._db = redis.Redis(
            host=host_address,
            password=password,
            db=db_num,
            decode_responses=True,
        )

    @classmethod
    def from_config_file(cls, config_path: Path) -> 'RedisDataLake':
        return cls(**load_yaml_as_dict(config_path))

    def set_data(self, key: str, data: str):
        self._db.set(key, data)

    def get_data(self, key: str) -> str:
        data = self._db.get(key)
        if data is None:
            raise KeyError(f'No data stored in db under key: {key}')
        return data


class S3DataLake(DataLake):
    """AWS S3 data lake key-value object storage."""

    def __init__(self, bucket_name: str):
        self._s3 = boto3.resource('s3')
        self._bucket = self._s3.Bucket(bucket_name)

    @classmethod
    def from_config_file(cls, config_path: Path) -> 'S3DataLake':
        return cls(**load_yaml_as_dict(config_path))

    def set_data(self, key: str, data: str):
        self._bucket.put_object(Key=key, Body=data.encode('utf-8'))

    def get_data(self, key: str) -> str:
        object_ = self._s3.Object(self._bucket, key).get()
        return object_['Body'].read().decode('utf-8')


class DataLakeImpl(Enum):
    REDIS = auto()
    S3BUCKET = auto()


class DataLakeFactory:
    def __init__(self, impl_type: DataLakeImpl, config_path: Path):
        self._impl_type = impl_type
        self._config_path = config_path

    def make(self):
        match self._impl_type:
            case DataLakeImpl.REDIS:
                return RedisDataLake.from_config_file(self._config_path)
            case DataLakeImpl.S3BUCKET:
                return S3DataLake.from_config_file(self._config_path)
            case _:
                raise ValueError('Selected data lake implementation is not supported or ' 'invalid')
