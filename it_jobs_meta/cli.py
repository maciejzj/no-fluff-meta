import argparse
from ast import parse
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional

from numpy import var

from it_jobs_meta.common.utils import setup_logging
from it_jobs_meta.dashboard.dashboard import (
    DashboardApp,
    DashboardProviders,
    DashboardDataProviderFactory,
)
from it_jobs_meta.data_pipeline.data_lake import RedisDataLake, S3DataLake, DataLakes
from it_jobs_meta.data_pipeline.data_pipeline import DataPipeline
from it_jobs_meta.data_pipeline.data_warehouse import (
    EtlPipeline,
    PandasEtlExtractionFromJsonStr,
    PandasEtlNoSqlLoadingEngine,
    PandasEtlSqlLoadingEngine,
    PandasEtlTransformationEngine,
    EtlLoaders,
)


class CliArgumentParser:
    def __init__(self):
        self._parser = argparse.ArgumentParser()
        self._subparsers = self._parser.add_subparsers(dest='command')
        self._build_main_command()
        self._build_pipeline_command()
        self._build_dashboard_command()
        self._args: Optional[dict[str, Any]] = None

    @property
    def args(self) -> argparse.Namespace:
        if self._args is None:
            self._args = vars(self._parser.parse_args())
        return self._args

    def extract_data_lake(self) -> tuple[DataLakes, Path]:
        match self.args:
            case {'redis': Path(), 's3_bucket': None}:
                return DataLakes.redis, self.args['redis']
            case {'s3_bucket': Path(), 'redis': None}:
                return DataLakes.s3bucket, self.args['s3_bucket']
            case _:
                raise ValueError(
                    'Parsed arguments resulted in unsupported or invalid data lake configuration'
                )

    def extract_data_warehouse(self) -> tuple[EtlLoaders, Path]:
        match self.args:
            case {'mongodb': Path(), 'sql': None}:
                return EtlLoaders.MONGODB, self.args['mongodb']
            case {'sql': Path(), 'mongodb': None}:
                return EtlLoaders.SQL, self.args['sql']
            case _:
                raise ValueError(
                    'Parsed arguments resulted in unsupported or invalid data warehouse configuration'
                )

    def extract_data_provider(self) -> tuple[DashboardProviders, Path]:
        match self.args:
            case {'mongodb': Path()}:
                return DashboardProviders.MONGODB, self.args['mongodb']
            case _:
                raise ValueError(
                    'Parsed arguments resulted in unsupported or invalid data warehouse configuration'
                )

    def _build_main_command(self):
        self._parser.add_argument(
            '-l', '--log-path', default=Path('var/it_jobs_meta.log'), type=Path
        )

    def _build_pipeline_command(self):
        parser_pipeline = self._subparsers.add_parser('pipeline')

        parser_pipeline.add_argument(
            '-c', '--schedule', metavar='CRON_EXPRESSION', action='store'
        )
        data_lake_arg_grp = parser_pipeline.add_mutually_exclusive_group(
            required=True
        )
        data_lake_arg_grp.add_argument(
            '-r', '--redis', metavar='CONFIG_PATH', action='store', type=Path
        )
        data_lake_arg_grp.add_argument(
            '-b',
            '--s3-bucket',
            metavar='CONFIG_PATH',
            action='store',
            type=Path,
        )

        data_warehouse_arg_grp = parser_pipeline.add_mutually_exclusive_group(
            required=True
        )
        data_warehouse_arg_grp.add_argument(
            '-m', '--mongodb', metavar='CONFIG_PATH', action='store', type=Path
        )
        data_warehouse_arg_grp.add_argument(
            '-s', '--sql', metavar='CONFIG_PATH', action='store', type=Path
        )

    def _build_dashboard_command(self):
        parser_dashboard = self._subparsers.add_parser('dashboard')

        parser_dashboard.add_argument(
            '-w', '--with-wsgi', action='store_true', default=False
        )

        data_warehouse_arg_grp = parser_dashboard.add_mutually_exclusive_group(
            required=True
        )
        data_warehouse_arg_grp.add_argument(
            '-m', '--mongodb', metavar='CONFIG_PATH', action='store', type=Path
        )