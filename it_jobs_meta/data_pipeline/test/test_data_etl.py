import math

import pandas as pd
import pytest

from it_jobs_meta.data_pipeline.data_etl import (
    EtlTransformationEngine,
    PandasEtlTransformationEngine,
)


@pytest.fixture
def postings_list_mock():
    return [
        {
            'id': 'ELGZSKOL',
            'name': 'Acaisoft Poland Sp. z.o.o',
            'location': {
                'places': [
                    {
                        'country': {'code': 'POL', 'name': 'Poland'},
                        'city': 'Warsaw',
                        'street': '',
                        'postalCode': '',
                        'url': 'sql-developer-node-js-acaisoft-poland-warsaw-elgzskol',  # noqa: E501
                    },
                    {
                        'country': {'code': 'POL', 'name': 'Poland'},
                        'city': 'Gdynia',
                        'street': '',
                        'postalCode': '',
                        'url': 'sql-developer-node-js-acaisoft-poland-gdynia-elgzskol',  # noqa: E501
                    },
                    {
                        'country': {'code': 'POL', 'name': 'Poland'},
                        'city': 'Białystok',
                        'street': '',
                        'postalCode': '',
                        'url': 'sql-developer-node-js-acaisoft-poland-bialystok-elgzskol',  # noqa: E501
                    },
                ],
                'fullyRemote': True,
                'covidTimeRemotely': False,
            },
            'posted': 1635163809168,
            'renewed': 1636895409168,
            'title': 'SQL Developer (Node.js)',
            'technology': 'sql',
            'logo': {
                'original': 'companies/logos/original/1615390311915.jpeg',
                'jobs_details': 'companies/logos/jobs_details/1615390311915.jpeg',
            },
            'category': 'backend',
            'seniority': ['Senior', 'Mid'],
            'url': 'sql-developer-node-js-acaisoft-poland-remote-elgzskol',
            'regions': ['pl'],
            'salary': {
                'from': 20000,
                'to': 25000,
                'type': 'b2b',
                'currency': 'PLN',
            },
            'flavors': ['it'],
            'topInSearch': False,
            'highlighted': False,
            'onlineInterviewAvailable': True,
            'referralBonus': math.nan,
            'referralBonusCurrency': math.nan,
        }
    ]


@pytest.fixture
def postings_response_json_dict_mock(postings_list_mock):
    return {
        'postings': postings_list_mock,
        'totalCount': 1,
    }


@pytest.fixture
def postings_metadata_dict_mock():
    return {
        'source_name': 'nofluffjobs',
        'obtained_datetime': '2021-12-01 08:30:05',
    }


@pytest.fixture
def postings_data_dict_mock(
    postings_metadata_dict_mock, postings_response_json_dict_mock
):
    return {
        'metadata': postings_metadata_dict_mock,
        'data': postings_response_json_dict_mock,
    }


class TestHappyPathPandasDataWarehouseETL:
    def setup_method(self, postings_list_mock):
        self.df = pd.DataFrame(postings_list_mock)
        self.transformer = PandasEtlTransformationEngine()

    def test_keeps_required_cols_correctly(self):
        result = self.transformer.select_required(self.df)
        for key in EtlTransformationEngine.COLS_TO_KEEP:
            assert key in result

    def test_extracts_remote_correctly(self):
        result = self.transformer.extract_remote(self.df)
        assert 'remote' in result
        assert result[result['id'] == 'ELGZSKOL']['remote'].iloc[0]

    def test_extracts_locations_correctly(self):
        result = self.transformer.extract_locations(self.df)
        assert 'city' in result
        assert (
            result[result['id'] == 'ELGZSKOL']['city'].iloc[0][0][0]
            == 'Warszawa'
        )
        assert (
            pytest.approx(
                result[result['id'] == 'ELGZSKOL']['city'].iloc[0][0][1], 1
            )
            == 52.2
        )
        assert (
            pytest.approx(
                result[result['id'] == 'ELGZSKOL']['city'].iloc[0][0][2], 1
            )
            == 21.0
        )

    def test_extracts_contract_type_correctly(self):
        result = self.transformer.extract_contract_type(self.df)
        assert 'contract_type' in result
        assert (
            result[result['id'] == 'ELGZSKOL']['contract_type'].iloc[0] == 'b2b'
        )

    def test_extracts_salaries_correctly(self):
        result = self.transformer.extract_salaries(self.df)
        assert 'salary_min' in result
        assert 'salary_max' in result
        assert 'salary_mean' in result
        assert result[result['id'] == 'ELGZSKOL']['salary_min'].iloc[0] == 20000
        assert result[result['id'] == 'ELGZSKOL']['salary_max'].iloc[0] == 25000
        assert (
            result[result['id'] == 'ELGZSKOL']['salary_mean'].iloc[0] == 22500
        )
