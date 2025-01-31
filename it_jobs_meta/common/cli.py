"""Command line parser for the it-jobs-meta application."""

import argparse
import logging
from pathlib import Path
from typing import Any

from it_jobs_meta.data_pipeline.data_etl import EtlLoaderImpl
from it_jobs_meta.data_pipeline.data_lake import DataLakeImpl


class CliArgumentParser:
    """Command line parser for the it-jobs-meta application."""

    PROG = 'it-jobs-meta'
    DESCRIPTION = 'Data pipeline and meta-analysis dashboard for IT job postings'
    PIPELINE_DESCRIPTION = (
        'Run data pipeline once or periodically, scrap data, store it in the '
        'data lake, load processed data to the data warehouse.'
    )
    DASHBOARD_DESCRIPTION = 'Run data visualization dashboard server.'
    LOG_LEVEL_OPTIONS = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
    }

    def __init__(self):
        self._args: dict[str, Any] | None = None
        self._parser = argparse.ArgumentParser(
            prog=self.PROG,
            description=self.DESCRIPTION,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        self._subparsers = self._parser.add_subparsers(dest='command', required=True)
        self._build_main_command()
        self._build_pipeline_command()
        self._build_dashboard_command()

    @property
    def args(self) -> dict[str, Any]:
        if self._args is None:
            self._args = vars(self._parser.parse_args())
        return self._args

    def extract_data_lake(self) -> tuple[DataLakeImpl, Path]:
        """Extract data lake setup from the arguments.

        :return: Tuple with the selected data lake implementation type and
            the config path.
        """
        match self.args:
            case {'redis': Path(), 's3_bucket': None}:
                return DataLakeImpl.REDIS, self.args['redis']
            case {'s3_bucket': Path(), 'redis': None}:
                return DataLakeImpl.S3BUCKET, self.args['s3_bucket']
            case _:
                raise ValueError(
                    'Parsed arguments resulted in unsupported or invalid data' ' lake configuration'
                )

    def extract_etl_loader(self) -> tuple[EtlLoaderImpl, Path]:
        """Get the ETL loader setup from the arguments.

        :return: Tuple with the selected etl loader implementation type and
            the config path.
        """
        match self.args:
            case {'mongodb': Path(), 'sql': None}:
                return EtlLoaderImpl.MONGODB, self.args['mongodb']
            case {'sql': Path(), 'mongodb': None}:
                return EtlLoaderImpl.SQL, self.args['sql']
            case _:
                raise ValueError(
                    'Parsed arguments resulted in unsupported or invalid ETL '
                    'loader configuration'
                )

    def _build_main_command(self):
        self._parser.add_argument(
            '-v',
            '--log-level',
            default='info',
            type=str,
            choices=self.LOG_LEVEL_OPTIONS.keys(),
            help='set verbosity/log level of the program',
        )
        self._parser.add_argument(
            '-l',
            '--log-path',
            default=Path('var/it_jobs_meta.log'),
            type=Path,
            help='path to the log file',
        )

    def _build_pipeline_command(self):
        parser_pipeline = self._subparsers.add_parser(
            'pipeline', description=self.PIPELINE_DESCRIPTION
        )

        # Execution schedule
        parser_pipeline.add_argument(
            '-c',
            '--schedule',
            metavar='CRON_EXPRESSION',
            action='store',
            type=str,
            help='schedule pipeline to run periodically with a cron expression',  # noqa: E501
        )

        # Data ingestion/source setup
        parser_pipeline.add_argument(
            '-a',
            '--from-archive',
            metavar='URL',
            action='store',
            default=None,
            type=str,
            help='obtain postings data from archive (URL must point to JSON in data lake storage format)',  # noqa: E501
        )

        # Data lake setup
        data_lake_arg_grp = parser_pipeline.add_mutually_exclusive_group()
        data_lake_arg_grp.add_argument(
            '-r',
            '--redis',
            metavar='CONFIG_PATH',
            action='store',
            type=Path,
            help='choose Redis as the data lake with the given config file',
        )
        data_lake_arg_grp.add_argument(
            '-b',
            '--s3-bucket',
            metavar='CONFIG_PATH',
            action='store',
            type=Path,
            help='choose S3 Bucket as the data lake with the given config file',  # noqa: E501
        )

        # Data warehouse setup
        etl_loader_arg_grp = parser_pipeline.add_mutually_exclusive_group(required=True)
        etl_loader_arg_grp.add_argument(
            '-m',
            '--mongodb',
            metavar='CONFIG_PATH',
            action='store',
            type=Path,
            help='choose MongoDB as the data warehouse with the given config file',  # noqa: E501,
        )
        etl_loader_arg_grp.add_argument(
            '-s',
            '--sql',
            metavar='CONFIG_PATH',
            action='store',
            type=Path,
            help='choose MariaDB as the data warehouse with the given config file',  # noqa: E501
        )

    def _build_dashboard_command(self):
        parser_dashboard = self._subparsers.add_parser('dashboard')

        parser_dashboard.add_argument(
            '-w',
            '--with-wsgi',
            action='store_true',
            default=False,
            help='run dashboard server with WSGI (in deployment mode)',
        )

        parser_dashboard.add_argument(
            '-l',
            '--label',
            metavar='LABEL',
            action='store',
            default=None,
            type=str,
            help='extra label to be displayed at the top navbar',
        )

        # Data provsion setup (from data warehouse)
        data_provider_arg_grp = parser_dashboard.add_mutually_exclusive_group(required=True)
        data_provider_arg_grp.add_argument(
            '-m',
            '--mongodb',
            metavar='CONFIG_PATH',
            action='store',
            type=Path,
            help='choose MongoDb as the data provider with the given config file',  # noqa: E501
        )
