import dataclasses
import datetime
import json
import logging
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import redis


@dataclass
class PostingsMetadata:
    source_name: str
    obtained_datetime: datetime


@dataclass
class PostingsData:
    metadata: PostingsMetadata
    data: Any


class PostingsDataSource(ABC):
    @abstractmethod
    def get() -> PostingsData:
        pass


class DataLake(ABC):
    @abstractmethod
    def set(self, key: str, data: str):
        pass

    @abstractmethod
    def get(self, key: str) -> str:
        pass


def make_key_for_data(dataset: PostingsData) -> str:
    timestamp = dataset.metadata.obtained_datetime.timestamp()
    source_name = dataset.metadata.source_name
    return f'{timestamp}_{source_name}'


def make_json_string(dataset: PostingsData) -> str:
    data_dict = dataclasses.asdict(dataset)
    json_string = json.dumps(data_dict, default=str)
    return json_string


class NoFluffJobsPostingsDataSource(PostingsDataSource):
    POSTINGS_API_URL_SOURCE = 'https://nofluffjobs.com/api/posting'
    SOURCE_NAME = 'nofluffjobs'

    @classmethod
    def get(cls) -> PostingsData:
        r = requests.get(cls.POSTINGS_API_URL_SOURCE)
        json_data = r.json()
        datetime_now = datetime.datetime.now()

        metadata = PostingsMetadata(
            source_name=cls.SOURCE_NAME,
            obtained_datetime=datetime_now)
        data = PostingsData(
            metadata=metadata,
            data=json_data)

        logging.info(
            f'Scraped new data from {cls.SOURCE_NAME}, on {datetime_now}.')
        return data


class RedisDataLake(DataLake):
    def __init__(self, host: str, port: int, db: int):
        self._db = redis.Redis(host=host, port=port, db=db)

    def set(self, key: str, data: str):
        self._db.set(key, data)

    def get(self, key: str) -> str:
        return self._get(key)


def main():
    data = NoFluffJobsPostingsDataSource.get()
    data_lake = RedisDataLake('0.0.0.0', 6379, 0)
    data_lake.set(make_key_for_data(data), make_json_string(data))


if __name__ == '__main__':
    main()


class MockResponse:
    @staticmethod
    def json():
        return {"mock_key": "mock_response"}


class TestNoFluffJobsPostingsDataSource:
    def test_returns_correct_metadata_source_name(self, mocker):
        mocker.patch('requests.get', return_value=MockResponse())
        results = NoFluffJobsPostingsDataSource.get()
        source_name = results.metadata.source_name
        assert source_name == NoFluffJobsPostingsDataSource.SOURCE_NAME

    def test_returns_correct_metadata_datetime(self, mocker):
        expected = datetime.datetime(2021, 12, 1, 8, 30, 5)
        datetime_mock = mocker.patch('datetime.datetime')
        datetime_mock.now.return_value = expected

        mocker.patch('requests.get', return_value=MockResponse())

        results = NoFluffJobsPostingsDataSource.get()
        obtained_datetime = results.metadata.obtained_datetime
        assert obtained_datetime == expected
