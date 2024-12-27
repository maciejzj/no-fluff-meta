"""Full data pipeline for job postings data from No Fluff Jobs."""

import datetime as dt
import logging
from pathlib import Path
from time import sleep

import croniter

from it_jobs_meta.data_pipeline.data_etl import (
    EtlLoaderFactory,
    EtlPipeline,
    PandasEtlExtractionFromJsonStr,
    PandasEtlMongodbLoadingEngine,
    PandasEtlTransformationEngine,
)
from it_jobs_meta.data_pipeline.data_ingestion import PostingsDataSource
from it_jobs_meta.data_pipeline.data_lake import DataLakeFactory


class DataPipeline:
    """Full data pipeline for job postings data from No Fluff Jobs.

    Includes data scraping, ingestion, data lake storage, and running ETL job.
    """

    def __init__(
        self,
        *,
        data_source: PostingsDataSource,
        data_lake_factory: DataLakeFactory | None,
        etl_loader_factory: EtlLoaderFactory,
    ):
        self._data_source = data_source
        self._data_lake_factory = data_lake_factory
        self._etl_loader_factory = etl_loader_factory

    def schedule(self, cron_expression: str):
        logging.info(
            f'Data pipeline scheduled with cron expression: {cron_expression} '
            'send SIGINT to stop'
        )

        cron = croniter.croniter(cron_expression, dt.datetime.now())

        try:
            while True:
                now = dt.datetime.now()
                timedelta_till_next_trigger = cron.get_next(dt.datetime) - now
                sleep(timedelta_till_next_trigger.total_seconds())
                self.run()
        except KeyboardInterrupt:
            logging.info('Data pipeline loop interrupted by user')

    def run(self):
        try:
            logging.info('Started data pipeline')

            logging.info('Attempting to perform data ingestion step')
            data = self._data_source.get()
            logging.info('Data ingestion succeeded')
            data_key = data.make_key_for_data()
            data_as_json = data.make_json_str_from_data()

            if self._data_lake_factory is not None:
                logging.info('Attempting to archive raw data in data lake')
                data_lake = self._data_lake_factory.make()
                data_lake.set_data(data_key, data.make_json_str_from_data())
                logging.info(f'Data archival succeeded, stored under "{data_key}" key')

            logging.info('Attempting to perform data warehousing step')
            etl_pipeline = EtlPipeline(
                PandasEtlExtractionFromJsonStr(),
                PandasEtlTransformationEngine(),
                self._etl_loader_factory.make(),
            )
            etl_pipeline.run(data_as_json)
            logging.info('Data warehousing succeeded')

            logging.info('Data pipeline succeeded')
        except Exception as e:
            logging.exception(e)
            raise


def main():
    """Demo main function for ad-hock tests.

    Reads postings data from test JSON file and feeds it to the ETL pipeline.
    """

    test_json_file_path = Path('it_jobs_meta/data_pipeline/test/1640874783_nofluffjobs.json')
    mongodb_config_path = Path('config/mongodb_config.yml')
    with open(test_json_file_path, 'r', encoding='utf-8') as json_data_file:
        data_as_json = json_data_file.read()
    etl_pipeline = EtlPipeline(
        PandasEtlExtractionFromJsonStr(),
        PandasEtlTransformationEngine(),
        PandasEtlMongodbLoadingEngine.from_config_file(mongodb_config_path),
    )
    etl_pipeline.run(data_as_json)


if __name__ == '__main__':
    main()
