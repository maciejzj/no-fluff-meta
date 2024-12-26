"""Job postings data ingestion and web scraping."""

import datetime as dt
from abc import ABC, abstractmethod

import requests

from it_jobs_meta.data_pipeline.data_formats import (
    NoFluffJObsPostingsData,
    PostingsData,
    PostingsMetadata,
)


class PostingsDataSource(ABC):
    """Source for fetching postings data from the web."""

    @abstractmethod
    def get(self) -> PostingsData:
        """Get a batch of postings data from the source."""


class NoFluffJobsPostingsDataSource(PostingsDataSource):
    """Source of postings data scraped using REST api from No Fluff Jobs."""

    POSTINGS_API_URL_SOURCE = 'https://nofluffjobs.com/api/posting'
    SOURCE_NAME = 'nofluffjobs'

    def get(self) -> PostingsData:
        """Get a snapshot of postings data from No Fluff Jobs in one batch."""
        response = requests.get(self.POSTINGS_API_URL_SOURCE)
        raw_data = response.json()
        datetime_now = dt.datetime.now()

        metadata = PostingsMetadata(source_name=self.SOURCE_NAME, obtained_datetime=datetime_now)
        data = NoFluffJObsPostingsData(metadata=metadata, raw_data=raw_data)

        return data


class ArchiveNoFluffJObsPostingsDataSource(PostingsDataSource):
    """Load postings data from archive under URL (from data lake or file)."""

    def __init__(self, posting_url: str):
        """
        Set source URL from archive.

        The data must be already archived in the data lake format.
        """
        self._posting_url = posting_url

    def get(self) -> PostingsData:
        """Get a posting from the archive."""
        response = requests.get(self._posting_url)
        data = NoFluffJObsPostingsData.from_json_str(response.text)
        return data


def main():
    """Demo main function for ad-hock tests.

    Gets the current postings from No Fluff Jobs and prints them as a json
    dict alongside the metadata.
    """
    data = NoFluffJobsPostingsDataSource().get()
    print(data.make_json_str_from_data())


if __name__ == '__main__':
    main()
