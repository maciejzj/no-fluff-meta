"""Dashboard layout and components stitching."""

from dataclasses import dataclass
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.development.base_component import Component as DashComponent
from plotly import graph_objects as go

from it_jobs_meta.dashboard.dashboard_components import Graph


# Static parametrization
@dataclass
class LayoutTemplateParameters:
    navbar_label: str | None = None


# Dynamically generated components
@dataclass
class LayoutDynamicContent:
    obtained_datetime: datetime
    graphs: dict[Graph, go.Figure]


# Mainly for long text
@dataclass
class DashboardTextualComponents:
    JUMBOTRON_TEXT_MD = '''
    Discover current trends in the IT job market in Poland through
    **interactive** graphs that are created based on real data gathered from
    **No Fluff Jobs**—one of the leading job walls in the country.
    '''

    ABOUT_TEXT_MD = '''
    This website serves as a data analysis service based on postings from
    [No Fluff Jobs](https://nofluffjobs.com), which is one of the most popular
    job walls for IT specialists in Poland. The data is gathered once a week
    and presented to you in form of beautiful plots, graphs, and maps. The
    meta-analysis of IT markets provides insights into leading technologies,
    salaries, job experience, and work locations distributions. The knowledge
    distilled from the analysis can help you with finding a job, evaluating
    salary for a vacancy, or planning your career in the IT sector. Have fun
    exploring the data!
    '''


def make_navbar(*, label: str | None = None) -> DashComponent:
    brand = 'IT Jobs Meta'
    if label is not None:
        brand = brand + f' ｜ {label}'

    navbar = dbc.NavbarSimple(
        dbc.NavLink(
            dbc.Button([html.I(className='fab fa-github'), ' GitHub'], color='dark'),
            href='https://github.com/maciejzj/no-fluff-meta',
            active=True,
            className='mr-0',
        ),
        brand=brand,
        className='bg-white',
    )
    return navbar


def make_jumbotron() -> DashComponent:
    jumbotron = html.Section(
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        children=[
                            html.H1('Weekly analysis of IT job offers in Poland'),
                            dcc.Markdown(DashboardTextualComponents.JUMBOTRON_TEXT_MD),
                            dbc.Button(
                                'To the data',
                                href='#data-section',
                                outline=True,
                                external_link=True,
                                active=True,
                                color='light',
                            ),
                        ],
                        className='p-5 text-white bg-dark rounded shadow-lg',
                    ),
                    lg=6,
                    className='mt-5',
                )
            ]
        )
    )
    return jumbotron


def make_about() -> DashComponent:
    about = html.Section(
        [
            html.H2('About'),
            dcc.Markdown(DashboardTextualComponents.ABOUT_TEXT_MD),
        ],
        className='text-center mt-5',
    )
    return about


def make_graphs_layout_header() -> DashComponent:
    div = html.Div(
        [
            html.H2('Data', id='data-container'),
            html.P(
                '''Although this website works fine on mobile devices, it
                is most convenient to explore more complex graphs on larger
                screens.'''
            ),
        ],
        className='text-center mt-5',
    )
    return div


def make_timeline_slider(obtained_datetime) -> DashComponent:
    slider_marks = dict(enumerate([t.strftime('%b %Y') for t in obtained_datetime]))
    return dcc.Slider(
        id='batch-slider',
        className='text-nowrap mx-3 my-5',
        step=None,
        marks=slider_marks,
        value=len(slider_marks) - 1,
    )


def make_categories_and_seniorities_graphs_layout(graphs: dict[Graph, dcc.Graph]) -> DashComponent:
    div = html.Div(
        [
            html.H3('Categories and seniorities', className='mt-4'),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.CATEGORIES_PIE_CHART],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        md=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.TECHNOLOGIES_PIE_CHART],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        md=6,
                    ),
                ],
                align='center',
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.CAT_TECH_SANKEY_CHART],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        md=7,
                    ),
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.SENIORITY_PIE_CHART],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        md=5,
                    ),
                ],
                align='center',
            ),
            dbc.Card(
                graphs[Graph.SENIORITIES_HISTOGRAM],
                className='mt-4 p-1 border-0 rounded shadow',
            ),
        ]
    )
    return div


def make_locations_and_remote_graphs_layout(graphs: dict[Graph, dcc.Graph]) -> DashComponent:
    div = html.Div(
        [
            html.H3('Locations and remote', className='mt-4'),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.REMOTE_PIE_CHART],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.SALARIES_MAP],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        lg=6,
                    ),
                ],
                align='center',
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.SALARIES_MAP_JUNIOR],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        lg=4,
                    ),
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.SALARIES_MAP_MID],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        lg=4,
                    ),
                    dbc.Col(
                        dbc.Card(
                            graphs[Graph.SALARIES_MAP_SENIOR],
                            className='mt-4 p-1 border-0 rounded shadow',
                        ),
                        lg=4,
                    ),
                ],
                align='center',
            ),
        ]
    )
    return div


def make_salaries_breakdown_graphs_layout(graphs: dict[Graph, dcc.Graph]) -> DashComponent:
    div = html.Div(
        [
            html.H3('Salaries breakdown', className='mt-4'),
            dbc.Card(
                graphs[Graph.TECHNOLOGIES_VIOLIN_PLOT], className='mt-4 p-1 border-0 rounded shadow'
            ),
            dbc.Card(
                graphs[Graph.CONTRACT_TYPE_VIOLIN_PLOT],
                className='mt-4 p-1 border-0 rounded shadow',
            ),
        ]
    )
    return div


def make_graphs_layout(graphs: dict[Graph, go.Figure]) -> list[DashComponent]:
    return [
        make_categories_and_seniorities_graphs_layout(graphs),
        make_locations_and_remote_graphs_layout(graphs),
        make_salaries_breakdown_graphs_layout(graphs),
    ]


def make_data_section_layout(
    obtained_datetime: datetime, graphs: dict[Graph, go.Figure]
) -> DashComponent:
    data_section = html.Section(
        [
            make_graphs_layout_header(),
            make_timeline_slider(obtained_datetime),
            html.Div(make_graphs_layout(graphs), id='graphs'),
        ],
        id='data-section',
    )
    return data_section


def make_footer() -> DashComponent:
    footer = html.Footer(
        [
            html.Div(html.Strong('Maciej Ziaja')),
            html.Div('maciejzj@icloud.com'),
            dbc.Button(
                [html.I(className='fab fa-github'), ' GitHub'],
                color='dark',
                href='https://github.com/maciejzj/no-fluff-meta',
                className='mt-2',
            ),
        ],
        className='m-3 p-3 text-center',
    )
    return footer


def make_layout(
    template_parameters: LayoutTemplateParameters,
    dynamic_content: LayoutDynamicContent,
) -> DashComponent:
    layout = html.Div(
        children=[
            make_navbar(label=template_parameters.navbar_label),
            dbc.Container(
                [
                    make_jumbotron(),
                    make_about(),
                    make_data_section_layout(
                        dynamic_content.obtained_datetime,
                        dynamic_content.graphs,
                    ),
                ],
                className='pb-3',
            ),
            make_footer(),
        ],
        className='w-100',
    )
    return layout
