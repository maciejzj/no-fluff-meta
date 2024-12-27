"""Data containers and wrappers for job postings data scrapped from the web."""

import dataclasses
import datetime as dt
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class PostingsMetadata:
    source_name: str
    obtained_datetime: dt.datetime


class PostingsData(ABC):
    @classmethod
    @abstractmethod
    def from_json_str(cls, json_str) -> 'PostingsData':
        """Make the data structure from JSON string.

        The input JSON should have keys:
            'metadata': Json dump of 'PostingsMetadata' with keys:
                'source_name': Name of the data source.
                'obtained_datetime': Timestamp with fmt 'YYYY-MM-DD HH:MM:SS'.
             'raw_data': Raw data in format of a JSON string.
        """

    @property
    @abstractmethod
    def metadata(self) -> PostingsMetadata:
        """Get the metadata associated with the data."""

    @property
    @abstractmethod
    def raw_data(self) -> Any:
        """Get the raw data scraped from the web, data schema is undefined."""

    @abstractmethod
    def make_key_for_data(self) -> str:
        """Make unique string identifier for the scraped data batch."""

    @abstractmethod
    def make_json_str_from_data(self) -> str:
        """Get the data in form of JSON string.

        The returned JSON should have keys:
            'metadata': JSON dump of 'PostingsMetadata' with keys:
                'source_name': Name of the data source.
                'obtained_datetime': Timestamp in format 'YYYY-MM-DD HH:MM:SS'.
            'raw_data': Raw data in format of a JSON string.
        """


class NoFluffJObsPostingsData(PostingsData):
    def __init__(self, metadata: PostingsMetadata, raw_data: Any):
        """Create with given metadata and raw scraped data."""
        self._raw_data = raw_data
        self._metadata = metadata

    @classmethod
    def from_json_str(cls, json_str: str) -> 'NoFluffJObsPostingsData':
        """Make the data structure from JSON string.

        The input JSON should have keys:
            'metadata': JSON dump of 'PostingsMetadata' with keys:
                'source_name': Name of the data source.
                'obtained_datetime': Timestamp with fmt 'YYYY-MM-DD HH:MM:SS'.
            'raw_data': Raw data in format of a JSON string.
        """
        data_dict = json.loads(json_str)
        source_name = data_dict['metadata']['source_name']
        obtained_datetime = dt.datetime.fromisoformat(data_dict['metadata']['obtained_datetime'])
        metadata = PostingsMetadata(source_name, obtained_datetime)
        raw_data = data_dict['raw_data']
        return cls(metadata, raw_data)

    @property
    def metadata(self) -> PostingsMetadata:
        return self._metadata

    @property
    def raw_data(self) -> Any:
        return self._raw_data

    def make_key_for_data(self) -> str:
        """Make unique string identifier for the scraped data batch.

        For this implementation it is a string of Unix epoch timestamp (with
        integer precision) and data source name ("nofluffjobs").
        """
        timestamp = int(self._metadata.obtained_datetime.timestamp())
        source_name = self._metadata.source_name
        return f'{timestamp}_{source_name}'

    def make_json_str_from_data(self) -> str:
        """Get the data in form of JSON string.

        The returned JSON should have keys:
            'metadata': JSON dump of 'PostingsMetadata' with keys:
                'source_name': Name of the data source.
                'obtained_datetime': Timestamp with fmt 'YYYY-MM-DD HH:MM:SS'.
            'raw_data': Raw scraped data in format of a JSON string. For
                No Fluff Jobs scraped data the structure is assumed to be:
                'postings': List of postings.
                'totalCount': The length of the list of postings.
        """
        meta_dict = dataclasses.asdict(self._metadata)
        datetime_ = meta_dict['obtained_datetime']
        meta_dict['obtained_datetime'] = datetime_.isoformat(' ', 'seconds')
        metadata_data_dict = {'metadata': meta_dict, 'raw_data': self.raw_data}
        return json.dumps(metadata_data_dict, default=str)
