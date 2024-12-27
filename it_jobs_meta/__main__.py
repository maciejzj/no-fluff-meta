"""Run the data pipeline or dashboard using CLI options."""

from it_jobs_meta.common.cli import CliArgumentParser
from it_jobs_meta.common.utils import setup_logging
from it_jobs_meta.dashboard.dashboard import (
    DashboardApp,
    DashboardDataProviderFactory,
    LayoutTemplateParameters,
)
from it_jobs_meta.data_pipeline.data_etl import EtlLoaderFactory
from it_jobs_meta.data_pipeline.data_ingestion import (
    ArchiveNoFluffJObsPostingsDataSource,
    NoFluffJobsPostingsDataSource,
)
from it_jobs_meta.data_pipeline.data_lake import DataLakeFactory
from it_jobs_meta.data_pipeline.data_pipeline import DataPipeline


def main():
    parser = CliArgumentParser()
    setup_logging(
        parser.args['log_path'],
        log_level=CliArgumentParser.LOG_LEVEL_OPTIONS[parser.args['log_level']],
    )

    match parser.args['command']:
        case 'pipeline':
            # Data ingestion/source setup
            if (url := parser.args['from_archive']) is not None:
                data_source = ArchiveNoFluffJObsPostingsDataSource(url)
            else:
                data_source = NoFluffJobsPostingsDataSource()

            # Data lake setup
            data_lake_setup = parser.extract_data_lake()
            if data_lake_setup is not None:
                data_lake_type, data_lake_cfg_path = parser.extract_data_lake()
                data_lake_factory = DataLakeFactory(data_lake_type, data_lake_cfg_path)
            else:
                data_lake_factory = None

            # Data warehouse setup
            warehouse_type, warehouse_cfg_path = parser.extract_etl_loader()
            etl_loader_factory = EtlLoaderFactory(warehouse_type, warehouse_cfg_path)

            # Pipeline composition
            data_pipeline = DataPipeline(
                data_source=data_source,
                data_lake_factory=data_lake_factory,
                etl_loader_factory=etl_loader_factory,
            )

            # Execution scheduling
            if parser.args['schedule'] is not None:
                data_pipeline.schedule(parser.args['schedule'])
            else:
                data_pipeline.run()

        case 'dashboard':
            provider_type, provider_cfg_path = parser.extract_data_provider()
            etl_loader_factory = DashboardDataProviderFactory(provider_type, provider_cfg_path)
            layout_parameters = LayoutTemplateParameters(navbar_label=parser.args['label'])
            app = DashboardApp(etl_loader_factory, layout_parameters)
            app.run(parser.args['with_wsgi'])


if __name__ == '__main__':
    main()
