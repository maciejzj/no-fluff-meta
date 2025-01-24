"""Dashboard server for job postings data visualization."""

import logging
from datetime import timedelta
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback
from dash.development.base_component import Component as DashComponent
from flask_caching import Cache as AppCache
from waitress import serve as wsgi_serve

from it_jobs_meta.common.utils import setup_logging
from it_jobs_meta.dashboard.dashboard_components import make_colormap, make_graphs
from it_jobs_meta.dashboard.data_provision import MongodbDashboardDataProvider
from it_jobs_meta.dashboard.layout import (
    LayoutDynamicContent,
    LayoutTemplateParameters,
    make_graphs_layout,
    make_layout,
)


class DashboardApp:
    def __init__(
        self,
        data_provider: MongodbDashboardDataProvider,
        layout_template_parameters: LayoutTemplateParameters,
        cache_timeout=timedelta(hours=6),
    ):
        self._app: dash.Dash | None = None
        self._cache: AppCache | None = None
        self._data_provider: MongodbDashboardDataProvider = data_provider
        self._layout_template_parameters: LayoutTemplateParameters = layout_template_parameters
        self._cache_timeout: timedelta = cache_timeout
        self._technologies_cmap: dict[str, str] | None = None
        self._categories_cmap: dict[str, str] | None = None
        self._seniorities_cmap: dict[str, str] | None = None

    @property
    def app(self) -> dash.Dash:
        if self._app is None:
            self._app = dash.Dash(
                'it-jobs-meta-dashboard',
                assets_folder=Path(__file__).parent / 'assets',
                external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
                title='IT Jobs Meta',
                meta_tags=[
                    {
                        'description': 'Weekly analysis of IT job offers in Poland',
                        'keywords': 'Programming, Software, IT, Jobs',
                        'name': 'viewport',
                        'content': 'width=device-width, initial-scale=1',
                    },
                ],
            )
        return self._app

    @property
    def cache(self) -> AppCache:
        if self._cache is None:
            self._cache = AppCache(
                self.app.server,
                config={'CACHE_TYPE': 'SimpleCache', 'CACHE_THRESHOLD': 2},
            )
        return self._cache

    def make_layout(self) -> DashComponent:
        logging.info('Rendering dashboard')
        logging.info('Attempting to retrieve data')
        metadata_df = self._data_provider.fetch_metadata()
        data_df = self._data_provider.fetch_data(metadata_df.iloc[-1]['batch_id'])
        self._technologies_cmap = make_colormap(
            self._data_provider.fetch_field_values_by_count('technology')
        )
        self._categories_cmap = make_colormap(
            self._data_provider.fetch_field_values_by_count('category')
        )
        self._seniorities_cmap = make_colormap(
            self._data_provider.fetch_field_values_by_count('seniority')
        )
        logging.info('Data retrieval succeeded')

        technologies_over_time_df = self._data_provider.fetch_field_count_over_time('technology')
        categories_over_time_df = self._data_provider.fetch_field_count_over_time('category')
        remote_over_time_df = self._data_provider.fetch_field_count_over_time('remote')
        seniority_over_time_df = self._data_provider.fetch_field_count_over_time('seniority')

        logging.info('Making layout')
        dynamic_content = self.make_dynamic_content(
            metadata_df,
            data_df,
            technologies_over_time_df,
            categories_over_time_df,
            remote_over_time_df,
            seniority_over_time_df,
            self._technologies_cmap,
            self._categories_cmap,
            self._seniorities_cmap,
        )
        layout = make_layout(self._layout_template_parameters, dynamic_content)
        logging.info('Making layout succeeded')
        logging.info('Rendering dashboard succeeded')
        return layout

    def register_callbacks(self) -> DashComponent:
        @callback(
            Output('graphs', 'children'),
            Input('batch-slider', 'value'),
            prevent_initial_call=True,
        )
        def update_graphs_section(value):
            metadata_df = self._data_provider.fetch_metadata()
            data_df = self._data_provider.fetch_data(metadata_df.iloc[value]['batch_id'])
            graphs = make_graphs(
                data_df, self._technologies_cmap, self._categories_cmap, self._seniorities_cmap
            )
            return make_graphs_layout(graphs)

    def run(self, with_wsgi=False):
        try:
            render_layout_memoized = self.cache.memoize(
                timeout=int(self._cache_timeout.total_seconds())
            )(self.make_layout)
            self.app.layout = render_layout_memoized
            self.register_callbacks()

            if with_wsgi:
                wsgi_serve(self.app.server, host='0.0.0.0', port='8080', url_scheme='https')
            else:
                self.app.run_server(debug=True, host='0.0.0.0', port='8080')

        except Exception as e:
            logging.exception(e)
            raise

    @staticmethod
    def make_dynamic_content(
        metadata_df: pd.DataFrame,
        data_df: pd.DataFrame,
        technologies_over_time_df: pd.DataFrame,
        categories_over_time_df: pd.DataFrame,
        remote_over_time_df: pd.DataFrame,
        seniority_over_time_df: pd.DataFrame,
        technologies_cmap: dict[str, str],
        categories_cmap: dict[str, str],
        seniorities_cmap: dict[str, str],
    ) -> LayoutDynamicContent:
        obtained_datetime = metadata_df['obtained_datetime']
        graphs = make_graphs(
            data_df,
            technologies_over_time_df,
            categories_over_time_df,
            remote_over_time_df,
            seniority_over_time_df,
            technologies_cmap,
            categories_cmap,
            seniorities_cmap,
        )
        return LayoutDynamicContent(obtained_datetime=obtained_datetime, graphs=graphs)


def main():
    """Run the demo dashboard with short cache timout (for development)."""
    setup_logging()
    layout_params = LayoutTemplateParameters()
    data_provider = MongodbDashboardDataProvider.from_config_file(Path('config/mongodb_config.yml'))
    app = DashboardApp(data_provider, layout_params, cache_timeout=timedelta(seconds=5))
    app.run()


if __name__ == '__main__':
    main()
