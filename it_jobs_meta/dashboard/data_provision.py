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

    def fetch_field_count_over_time(self, field: str) -> pd.DataFrame:
        client: MongoClient
        with MongoClient(
            self.host, self.port, username=self.user_name, password=self.password
        ) as client:
            db: Database = client[self.db_name]
            collection = db['postings']

            return pd.json_normalize(
                collection.aggregate(
                    [
                        # Explode multi-value fields
                        {
                            "$unwind": f"${field}",
                        },
                        # Group and count in respect to the field and batch id
                        {
                            "$group": {
                                "_id": {"batch_id": "$batch_id", field: f"${field}"},
                                "count": {"$count": {}},
                                "salary_mean": { "$avg": "$salary_mean" }
                            }
                        },
                        # Join with the metadata collection to get the obtained_datetime
                        {
                            "$lookup": {
                                "from": "metadata",
                                "localField": f"_id.batch_id",
                                "foreignField": "batch_id",
                                "as": "metadata",
                            }
                        },
                        # Replace batch_id with obtained_datetime
                        {
                            "$addFields": {
                                "obtained_datetime": {
                                    "$arrayElemAt": ["$metadata.obtained_datetime", 0]
                                }
                            }
                        },
                        # Reshape the output document
                        {
                            "$project": {
                                field: f"$_id.{field}",
                                "count": 1,
                                "obtained_datetime": 1,
                                "salary_mean": 1,
                                "_id": 0.0,
                            }
                        },
                    ]
                )
            )

    def fetch_field_values_by_count(self, field: str) -> list[str]:
        client: MongoClient
        with MongoClient(
            self.host, self.port, username=self.user_name, password=self.password
        ) as client:
            db: Database = client[self.db_name]
            collection = db['postings']

            return [
                doc["_id"]
                for doc in collection.aggregate(
                    [
                        {"$match": {field: {"$ne": None}}},
                        {"$unwind": f"${field}"},
                        {"$sortByCount": f"${field}"},
                    ]
                )
            ]
