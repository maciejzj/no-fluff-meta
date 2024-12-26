"""Data provision and data source for the data dashboard."""

from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path

import pandas as pd
import pymongo

from it_jobs_meta.common.utils import load_yaml_as_dict


class DashboardDataProvider(ABC):
    @abstractmethod
    def gather_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Gather data for the dashboard.

        :return: Tuple with metadata and data dataframes as (metadata_df,
            data_df)
        """


class MongodbDashboardDataProvider(DashboardDataProvider):
    def __init__(
        self,
        user_name: str,
        password: str,
        host: str,
        db_name: str,
        port=27017,
    ):
        self._db_client: pymongo.MongoClient = pymongo.MongoClient(
            f'mongodb://{user_name}:{password}@{host}:{port}'
        )
        self._db = self._db_client[db_name]

    @classmethod
    def from_config_file(cls, config_file_path: Path) -> 'MongodbDashboardDataProvider':
        return cls(**load_yaml_as_dict(config_file_path))

    def gather_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Gather data for the dashboard.

        :return: Tuple with metadata and data dataframes as (metadata_df,
            data_df)
        """
        metadata_df = pd.json_normalize(self._db['metadata'].find())
        postings_df = pd.json_normalize(self._db['postings'].find())
        if metadata_df.empty or postings_df.empty:
            raise RuntimeError('Data gather for the dashboard resulted in empty datasets')
        return metadata_df, postings_df


class DashboardProviderImpl(Enum):
    MONGODB = auto()


class DashboardDataProviderFactory:
    def __init__(self, impl_type: DashboardProviderImpl, config_path: Path):
        self._impl_type = impl_type
        self._config_path = config_path

    def make(self) -> DashboardDataProvider:
        match self._impl_type:
            case DashboardProviderImpl.MONGODB:
                return MongodbDashboardDataProvider.from_config_file(self._config_path)
            case _:
                raise ValueError(
                    'Selected data provider implementation is not supported ' 'or invalid'
                )
