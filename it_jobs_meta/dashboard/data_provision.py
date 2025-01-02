"""Data provision and data source for the data dashboard."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self

import pandas as pd
from pymongo import MongoClient
from pymongo.synchronous.database import Database

from it_jobs_meta.common.utils import load_yaml_as_dict


class DashboardDataProvider(ABC):
    @abstractmethod
    def fetch_metadata(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def fetch_data(self, batch_id: str) -> pd.DataFrame:
        pass


class MongodbDashboardDataProvider(DashboardDataProvider):
    def __init__(self, user_name: str, password: str, host: str, db_name: str, port=27017):
        self.user_name = user_name
        self.password = password
        self.host = host
        self.db_name = db_name
        self.port = port

    @classmethod
    def from_config_file(cls, config_file_path: Path) -> Self:
        return cls(**load_yaml_as_dict(config_file_path))

    def fetch_metadata(self) -> pd.DataFrame:
        client: MongoClient
        with MongoClient(
            self.host, self.port, username=self.user_name, password=self.password
        ) as client:
            db: Database = client[self.db_name]
            df = pd.json_normalize(db['metadata'].find().sort('obtained_datetime'))
            if len(df) == 0:
                raise ValueError('Found no metadata, dashboard cannot be made')
            return df

    def fetch_data(self, batch_id: str | None = None) -> pd.DataFrame:
        client: MongoClient
        with MongoClient(
            self.host, self.port, username=self.user_name, password=self.password
        ) as client:
            db: Database = client[self.db_name]
            collection = db['postings']

            if batch_id is not None:
                df = pd.json_normalize(collection.find({'batch_id': batch_id}))
            else:
                df = pd.json_normalize(collection.find())

            if len(df) == 0:
                raise ValueError('Found no data, dashboard cannot be made')
            return df
