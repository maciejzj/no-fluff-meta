"""Data dashboard components and graphs."""

from enum import Enum, auto
from typing import Any

import numpy as np
import pandas as pd
from dash import dcc
from plotly import express as px
from plotly import graph_objects as go
from plotly.colors import qualitative
from sklearn import preprocessing

SENIORITIES_ORDER = ['Trainee', 'Junior', 'Mid', 'Senior', 'Expert']


def get_n_most_frequent_vals_in_col(col: pd.Series, n: int) -> list[Any]:
    return col.value_counts().nlargest(n).index.to_list()


def get_rows_with_n_most_frequent_vals_in_col(
    df: pd.DataFrame, col_name: str, n: int
) -> pd.DataFrame:
    n_most_freq = get_n_most_frequent_vals_in_col(df[col_name], n)
    return df[df[col_name].isin(n_most_freq)]


def move_legend_to_top(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'xanchor': 'right',
            'y': 1,
            'x': 1,
        }
    )
    return fig


def center_title(fig: go.Figure) -> go.Figure:
    fig.update_layout(title_x=0.5)
    return fig


def make_colormap(values: list[str]) -> dict[str, str]:
    palette = qualitative.Plotly + qualitative.Pastel + qualitative.Pastel2
    extended_palette = palette * (len(values) // len(palette) + 1)
    return dict(zip(values, extended_palette[: len(values)]))


class Graph(Enum):
    REMOTE_PIE_CHART = auto()
    TECHNOLOGIES_PIE_CHART = auto()
    CATEGORIES_PIE_CHART = auto()
    SENIORITY_PIE_CHART = auto()
    CAT_TECH_SANKEY_CHART = auto()
    SALARIES_MAP = auto()
    SENIORITIES_HISTOGRAM = auto()
    TECHNOLOGIES_VIOLIN_PLOT = auto()
    CONTRACT_TYPE_VIOLIN_PLOT = auto()
    SALARIES_MAP_JUNIOR = auto()
    SALARIES_MAP_MID = auto()
    SALARIES_MAP_SENIOR = auto()

    TECHNOLOGIES_OVER_TIME = auto()


class TechnologiesOverTime:
    @classmethod
    def make_fig(
        cls, technologies_over_time_df: pd.DataFrame, cmap: dict[str, str] | None = None
    ) -> go.Figure:

        top_technologies_per_time = (
            technologies_over_time_df.sort_values(
                ["obtained_datetime", "count"], ascending=[True, False]
            )
            .groupby("obtained_datetime")
            .head(10)
        )

        fig = px.line(
            top_technologies_per_time,
            x="obtained_datetime",
            y="salary_mean",
            color="technology",
            color_discrete_map=cmap,
        )
        return fig


def make_graphs(
    postings_df: pd.DataFrame,
    technologies_over_time_df: pd.DataFrame,
    categories_over_time_df: pd.DataFrame,
    remote_over_time_df: pd.DataFrame,
    seniority_over_time_df: pd.DataFrame,
    technologies_cmap: dict[str, str],
    categories_cmap: dict[str, str],
    seniorities_cmap: dict[str, str],
) -> dict[Graph, dcc.Graph]:
    figures = {
        Graph.REMOTE_PIE_CHART: RemotePieChart.make_fig(postings_df),
        Graph.TECHNOLOGIES_PIE_CHART: TechnologiesPieChart.make_fig(postings_df, technologies_cmap),
        Graph.CATEGORIES_PIE_CHART: CategoriesPieChart.make_fig(postings_df, categories_cmap),
        Graph.SENIORITY_PIE_CHART: SeniorityPieChart.make_fig(postings_df, seniorities_cmap),
        Graph.CAT_TECH_SANKEY_CHART: CategoriesTechnologiesSankeyChart.make_fig(
            postings_df, technologies_cmap, categories_cmap
        ),
        Graph.SALARIES_MAP: SalariesMap.make_fig(postings_df),
        Graph.SENIORITIES_HISTOGRAM: SenioritiesHistogram.make_fig(postings_df, seniorities_cmap),
        Graph.TECHNOLOGIES_VIOLIN_PLOT: TechnologiesViolinChart.make_fig(postings_df),
        Graph.CONTRACT_TYPE_VIOLIN_PLOT: ContractTypeViolinChart.make_fig(postings_df),
        Graph.SALARIES_MAP_JUNIOR: SalariesMapJunior.make_fig(postings_df),
        Graph.SALARIES_MAP_MID: SalariesMapMid.make_fig(postings_df),
        Graph.SALARIES_MAP_SENIOR: SalariesMapSenior.make_fig(postings_df),
        Graph.TECHNOLOGIES_OVER_TIME: TechnologiesOverTime.make_fig(
            technologies_over_time_df, technologies_cmap
        ),
    }

    graphs = {graph_key: dcc.Graph(figure=figures[graph_key]) for graph_key in figures}
    return graphs


class TechnologiesPieChart:
    TITLE = 'Main technology'
    N_MOST_FREQ = 12

    @classmethod
    def make_fig(cls, postings_df: pd.DataFrame, cmap: dict[str, str] | None = None) -> go.Figure:
        tech_most_freq_df = get_rows_with_n_most_frequent_vals_in_col(
            postings_df, 'technology', cls.N_MOST_FREQ
        )
        technology_counts = tech_most_freq_df['technology'].value_counts().reset_index()
        technology_counts.columns = ['technology', 'count']

        fig = px.pie(
            technology_counts,
            names='technology',
            color='technology',
            values='count',
            title=cls.TITLE,
            color_discrete_map=cmap,
        )
        fig.update_traces(textposition='inside')
        fig = center_title(fig)
        return fig


class CategoriesPieChart:
    TITLE = 'Main category'
    N_MOST_FREQ = 12

    @classmethod
    def make_fig(cls, postings_df: pd.DataFrame, cmap: dict[str, str] | None = None) -> go.Figure:
        # Get the most frequent categories and their counts
        cat_largest_df = get_rows_with_n_most_frequent_vals_in_col(
            postings_df, 'category', cls.N_MOST_FREQ
        )
        category_counts = cat_largest_df['category'].value_counts().reset_index()
        category_counts.columns = ['category', 'count']

        # Create a pie chart with count values
        fig = px.pie(
            category_counts,
            names='category',
            color='category',
            values='count',
            title=cls.TITLE,
            color_discrete_map=cmap,
        )
        fig.update_traces(textposition='inside')
        fig = center_title(fig)
        return fig


class CategoriesTechnologiesSankeyChart:
    TITLE = 'Categories and technologies share'
    N_MOST_FREQ_CAT = 12
    N_MOST_FREQ_TECH = 12
    MIN_FLOW = 12

    @classmethod
    def make_fig(
        cls,
        postings_df: pd.DataFrame,
        tech_cmap: dict[str, str] | None = None,
        catgr_cmap: dict[str, str] | None = None,
    ) -> go.Figure:
        cat_most_freq = get_n_most_frequent_vals_in_col(
            postings_df['category'], cls.N_MOST_FREQ_CAT
        )
        tech_most_freq = get_n_most_frequent_vals_in_col(
            postings_df['technology'], cls.N_MOST_FREQ_TECH
        )
        cat_tech_most_freq_df = postings_df[
            postings_df['category'].isin(cat_most_freq)
            & postings_df['technology'].isin(tech_most_freq)
        ]

        catgrp = cat_tech_most_freq_df.groupby('category')['technology'].value_counts()
        catgrp = catgrp.drop(catgrp[catgrp < cls.MIN_FLOW].index)
        catgrp = catgrp.dropna()

        catgrp_list = catgrp.index.to_list()
        sources = [el[0] for el in catgrp_list]
        targets = [el[1] for el in catgrp_list]
        values = catgrp.to_list()

        label_encoder = preprocessing.LabelEncoder()
        label_encoder.fit(sources + targets)
        sources_e = label_encoder.transform(sources)
        targets_e = label_encoder.transform(targets)

        unique_labels = np.unique(sources + targets)
        if tech_cmap is not None and catgr_cmap is not None:
            colors = [catgr_cmap.get(label) or tech_cmap.get(label) for label in unique_labels]
        else:
            colors = None

        fig = go.Figure(
            data=[
                go.Sankey(
                    node={'label': unique_labels, 'color': colors},
                    link={'source': sources_e, 'target': targets_e, 'value': values},
                )
            ]
        )
        fig.update_layout(title_text=cls.TITLE)
        fig = center_title(fig)
        return fig


class SeniorityPieChart:
    TITLE = 'Seniority'

    @classmethod
    def make_fig(cls, postings_df: pd.DataFrame, cmap: dict[str, str] | None = None) -> go.Figure:
        postings_df = postings_df.explode('seniority')
        seniority_counts = postings_df['seniority'].value_counts().reset_index()
        seniority_counts.columns = ['seniority', 'count']

        fig = px.pie(
            seniority_counts,
            values='count',
            color='seniority',
            names='seniority',
            title=cls.TITLE,
            color_discrete_map=cmap,
            category_orders={'seniority': SENIORITIES_ORDER},
        )
        fig = center_title(fig)
        return fig


class SenioritiesHistogram:
    TITLE = 'Histogram'
    MAX_SALARY = 40000

    @classmethod
    def make_fig(cls, postings_df, cmap: dict[str, str] | None = None) -> go.Figure:
        postings_df = postings_df.explode('seniority')
        postings_df = postings_df[postings_df['salary_mean'] < cls.MAX_SALARY]
        postings_df = postings_df[postings_df['salary_mean'] > 0]

        fig = px.histogram(
            postings_df,
            x='salary_mean',
            color='seniority',
            nbins=50,
            title=cls.TITLE,
            color_discrete_map=cmap,
            category_orders={'seniority': SENIORITIES_ORDER},
        )
        fig = fig.update_layout(
            legend_title_text=None,
            xaxis_title_text='Mean salary (PLN)',
            yaxis_title_text='Count',
        )
        fig = move_legend_to_top(fig)
        return fig


class RemotePieChart:
    TITLE = 'Fully remote work possible'

    @classmethod
    def make_fig(cls, postings_df: pd.DataFrame) -> go.Figure:
        remote_df = postings_df['remote'].replace({True: 'Yes', False: 'No'})

        fig = px.pie(
            remote_df, names='remote', title=cls.TITLE, category_orders={'remote': ['Yes', 'No']}
        )
        fig = center_title(fig)
        return fig


class SalariesMap:
    TITLE = 'Mean salary by location (PLN)'
    N_MOST_FREQ = 15
    POLAND_LAT, POLAND_LON = 52.0, 19.0
    PROJECTION_SCALE = 10

    @classmethod
    def make_fig(cls, postings_df) -> go.Figure:
        postings_df = postings_df.explode('city').dropna(subset=['city'])
        postings_df[['city', 'lat', 'lon']] = postings_df['city'].transform(
            lambda city: pd.Series([city[0], city[1], city[2]])
        )

        postings_df = get_rows_with_n_most_frequent_vals_in_col(
            postings_df, 'city', cls.N_MOST_FREQ
        )
        job_counts = postings_df.groupby('city')['_id'].count()
        salaries = postings_df.groupby('city')[['salary_mean', 'lat', 'lon']].mean()
        salaries['salary_mean'] = salaries['salary_mean'].round()
        cities_salaries = pd.concat([job_counts.rename('job_counts'), salaries], axis=1)
        cities_salaries = cities_salaries.reset_index()

        fig = px.scatter_geo(
            cities_salaries,
            lat='lat',
            lon='lon',
            size='job_counts',
            color='salary_mean',
            title=cls.TITLE,
            labels={
                'salary_mean': 'Mean salary',
                'job_counts': 'Number of jobs',
            },
            hover_data={'city': True, 'lat': False, 'lon': False},
        )

        fig.update_layout(
            geo=dict(
                scope='europe',
                center={'lat': cls.POLAND_LAT, 'lon': cls.POLAND_LON},
                projection_scale=cls.PROJECTION_SCALE,
            )
        )

        fig = center_title(fig)
        return fig


class SalariesMapFilteredBySeniority:
    @classmethod
    def make_fig(
        cls,
        postings_df,
        seniority: str,
    ) -> go.Figure:
        postings_df = postings_df.explode('seniority')
        postings_df = postings_df[postings_df['seniority'] == seniority]

        fig = SalariesMap.make_fig(postings_df)
        fig = fig.update_layout(margin={'l': 65, 'r': 65, 'b': 60})
        return fig


class SalariesMapJunior:
    TITLE = 'Mean salary for Juniors'

    @classmethod
    def make_fig(
        cls,
        postings_df,
    ) -> go.Figure:
        fig = SalariesMapFilteredBySeniority.make_fig(postings_df, 'Junior')
        fig.update_layout(title=cls.TITLE)
        fig.update_coloraxes(showscale=False)
        fig = center_title(fig)
        return fig


class SalariesMapMid:
    TITLE = 'Mean salary for Mids'

    @classmethod
    def make_fig(
        cls,
        postings_df,
    ) -> go.Figure:
        fig = SalariesMapFilteredBySeniority.make_fig(postings_df, 'Mid')
        fig.update_layout(title=cls.TITLE)
        fig.update_coloraxes(showscale=False)
        fig = center_title(fig)
        return fig


class SalariesMapSenior:
    TITLE = 'Mean salary for Seniors'

    @classmethod
    def make_fig(cls, postings_df) -> go.Figure:
        fig = SalariesMapFilteredBySeniority.make_fig(postings_df, 'Senior')
        fig.update_layout(title=cls.TITLE)
        fig.update_coloraxes(showscale=False)
        fig = center_title(fig)
        return fig


class TechnologiesViolinChart:
    TITLE = 'Violin plot split by seniority'
    MAX_SALARY = 35000
    N_MOST_FREQ_TECH = 8

    @classmethod
    def make_fig(cls, postings_df, seniorities_cmap: dict[str, str] | None = None) -> go.Figure:
        postings_df = postings_df.explode('seniority')
        tech_most_freq = get_rows_with_n_most_frequent_vals_in_col(
            postings_df, 'technology', cls.N_MOST_FREQ_TECH
        )
        limited = tech_most_freq[tech_most_freq['salary_mean'] < cls.MAX_SALARY]
        limited = limited[limited['seniority'].isin(('Junior', 'Mid', 'Senior'))]
        # Plotly has problems with creating violin plots if there are too few
        # samples, we filter out seniority and technology paris for which
        # there aren't enough data points to make a nice curve
        limited = limited.groupby(['seniority', 'technology']).filter(
            lambda x: x['technology'].count() > 3
        )

        fig = px.violin(
            limited,
            x='salary_mean',
            y='technology',
            color='seniority',
            violinmode='overlay',
            title=cls.TITLE,
            points=False,
        )
        fig = move_legend_to_top(fig)
        fig = fig.update_traces(side='positive', width=1.5, spanmode='hard', meanline_visible=True)
        fig = fig.update_layout(
            height=600,
            xaxis_title_text='Mean salary (PLN)',
            yaxis_title_text='Technology',
            legend_title_text=None,
        )
        fig = center_title(fig)
        return fig


class ContractTypeViolinChart:
    TITLE = 'Violin plot split by contract'
    MAX_SALARY = 40000
    N_MOST_FREQ_TECH = 8

    @classmethod
    def make_fig(cls, postings_df) -> go.Figure:
        tech_most_freq = get_rows_with_n_most_frequent_vals_in_col(
            postings_df, 'technology', cls.N_MOST_FREQ_TECH
        )
        limited = tech_most_freq[tech_most_freq['salary_mean'] < cls.MAX_SALARY]
        b2b_df = limited[limited['contract_type'] == 'B2B']
        perm_df = limited[limited['contract_type'] == 'Permanent']

        fig = go.Figure()
        fig.add_trace(
            go.Violin(
                x=b2b_df['technology'],
                y=b2b_df['salary_mean'],
                legendgroup='B2B',
                scalegroup='B2B',
                name='B2B',
                side='negative',
                spanmode='hard',
                points=False,
            )
        )
        fig.add_trace(
            go.Violin(
                x=perm_df['technology'],
                y=perm_df['salary_mean'],
                legendgroup='Permanent',
                scalegroup='Permanent',
                name='Permanent',
                side='positive',
                spanmode='hard',
                points=False,
            )
        )
        fig.update_traces(meanline_visible=True, width=0.9)
        fig.update_layout(
            violingap=0,
            violinmode='overlay',
            yaxis_title_text='Mean salary (PLN)',
            xaxis_title_text='Technology',
            title=cls.TITLE,
        )
        fig = move_legend_to_top(fig)
        fig = center_title(fig)
        return fig
