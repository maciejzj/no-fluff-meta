"""Data Extraction, Transformations, and Loading for the job postings data."""

import dataclasses
import uuid
from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import Generic, TypeVar

import pandas as pd
import sqlalchemy as db
from pymongo import MongoClient

from it_jobs_meta.common.utils import load_yaml_as_dict
from it_jobs_meta.data_pipeline.data_formats import NoFluffJObsPostingsData
from it_jobs_meta.data_pipeline.data_validation import (
    METADATA_JSON_SCEHMA,
    POSTINGS_JSON_SCHEMA,
    Schemas,
)
from it_jobs_meta.data_pipeline.geolocator import Geolocator

# Data type used internally by the data transformation pipeline.
ProcessDataType = TypeVar('ProcessDataType')
# Data type accepted as the input to the data pipeline by the data extraction
# engine.
PipelineInputType = TypeVar('PipelineInputType')
# E.g. Data pipeline input data type is JSON string, and internal processing
# data type is Pandas Data Frame.


class EtlExtractionEngine(Generic[PipelineInputType, ProcessDataType], ABC):
    """Extraction engine for the ETL pipeline.

    Should handle inputs in the PipelineInputType and provide the pipeline with
    the PipelineInputType data.
    """

    @abstractmethod
    def extract(self, input_: PipelineInputType) -> tuple[ProcessDataType, ProcessDataType]:
        """Extract data from the input and get it the pipeline compatible form.

        :return: Tuple with metadata and data dataframes (metadata, data).
        """


class EtlTransformationEngine(Generic[ProcessDataType], ABC):
    """ETL operations actions template on the given processing data type.

    Includes constants with values to drop, replace, or transform, and
    interfaces for methods necessary to build the processing pipeline.
    """

    # Columns that are unique per posting and can be used to identify duplicates.
    COLS_UNIQUE_IDENTITY = ['name', 'posted', 'title']

    # Columns to pick for further processing, the rest should be dropped.
    COLS_TO_KEEP = [
        'id',
        'name',
        'location',
        'posted',
        'title',
        'technology',
        'category',
        'seniority',
        'salary',
    ]

    # Look at the ETL pipeline implementation to see the predefined order of
    # the string formatting operations in columns.
    COLS_TO_LOWER = [
        'technology',
    ]

    # Replace strings in columns specified by dict keys.
    VALS_TO_REPLACE = {
        'technology': {
            'node.js': 'node',
            'angular': 'javascript',
            'react': 'javascript',
        }
    }

    # Apply transformation like 'businessAnalyst' -> 'business Analyst'
    COLS_TO_SPLIT_ON_CAPITAL_LETTERS = [
        'category',
    ]

    # Title case text is like "Sample Text".
    COLS_TO_TITLE_CASE = ['category']

    # Capitalized text is like: "Sample text".
    COLS_TO_CAPITALIZE = ['technology', 'contract_type']

    # Names that require specific mappings instead of normal capitalizations.
    # Input strings should be transformed to lower before applying these cases.
    CAPITALIZE_SPECIAL_NAMES = {
        'technology': {
            '.net': '.Net',
            'aws': 'AWS',
            'ios': 'iOS',
            'javascript': 'JavaScript',
            'php': 'PHP',
            'sql': 'SQL',
            'api': 'API',
            'ci': 'CI',
            'cd': 'CD',
            'ci/cd': 'CI/CD',
            'c/c++': 'C/C++',
        },
        'contract_type': {
            'b2b': 'B2B',
            'B2b': 'B2B',
        },
    }

    # Limit locations to the given countries, use ISO 3166-1alpha2 codes.
    COUNTRY_FILTERS = ['pl']

    # Minimum mean salary based on minimum wage in Poland (we assume that lower salaries are mistakes).
    SALARY_CURRENCY = 'PLN'
    MIN_MEAN_SALARY = 3500

    @abstractmethod
    def select_required(self, data: ProcessDataType) -> ProcessDataType:
        """Select only the required columns specified in COLS_TO_KEEP."""

    @abstractmethod
    def drop_duplicates(self, data: ProcessDataType) -> ProcessDataType:
        """Drop duplicated rows in the dataset based on COLS_UNIQUE_IDENTITY."""

    @abstractmethod
    def unify_to_lower(self, data: ProcessDataType) -> ProcessDataType:
        """Unify strings to lower capitalization."""

    @abstractmethod
    def replace_values(self, data: ProcessDataType) -> ProcessDataType:
        """Replace values specified in COLS_TO_DROP."""

    @abstractmethod
    def split_on_capitals(self, data: ProcessDataType) -> ProcessDataType:
        """Transform like 'businessAnalyst' -> 'business Analyst'."""

    @abstractmethod
    def to_title_case(self, data: ProcessDataType) -> ProcessDataType:
        """Transform columns in COLS_TO_TITLE_CASE to title case.

        Title case text is like "Sample Text".
        """

    @abstractmethod
    def to_capitalized(self, data: ProcessDataType) -> ProcessDataType:
        """Capitalize columns in COLS_TO_CAPITALIZE.

        Capitalized text is like "Sample text".
        """

    @abstractmethod
    def extract_remote(self, data: ProcessDataType) -> ProcessDataType:
        """Extract remote work option and place it in the "remote" column."""

    @abstractmethod
    def extract_locations(self, data: ProcessDataType) -> ProcessDataType:
        """Extract work location as cities and place them in the "city" column.

        Should ensure consistent naming and coordinates for given locations.
        The values in the "city" column should be gathered in a tuple of
        (city_name, latitude, longitude). The results should be limited to the
        countries in COUNTRY_FILTERS.
        """

    @abstractmethod
    def extract_contract_type(self, data: ProcessDataType) -> ProcessDataType:
        """Extract contract type and place it in the "contract_type" column."""

    @abstractmethod
    def extract_salaries(self, data: ProcessDataType) -> ProcessDataType:
        """Extract salaries to columns: "salary_max", "min", "salary_mean"."""

    @abstractmethod
    def unify_missing_values(self, data: ProcessDataType) -> ProcessDataType:
        """Unify missing values (NaNs, empty, etc.) into Nones."""


class EtlLoadingEngine(Generic[ProcessDataType], ABC):
    """Loader for placing processing results in databases."""

    @abstractmethod
    def load_tables_to_warehouse(self, metadata: ProcessDataType, data: ProcessDataType):
        """Load processed data into a database."""


class EtlPipeline(Generic[ProcessDataType, PipelineInputType]):
    """ETL pipeline coordinating extraction, transformations, and loading."""

    def __init__(
        self,
        extraction_engine: EtlExtractionEngine[PipelineInputType, ProcessDataType],
        transformation_engine: EtlTransformationEngine[ProcessDataType],
        loading_engine: EtlLoadingEngine[ProcessDataType],
    ):
        """Data pipeline runner for ETL jobs.

        Notice that the extraction, transformation, and loading engines must
        work on the same ProcessDataType type to build a proper pipeline.
        """

        self._extraction_engine = extraction_engine
        self._transformation_engine = transformation_engine
        self._loading_engine = loading_engine

    def run(self, input_: PipelineInputType):
        metadata, data = self.extract(input_)
        data = self.transform(data)
        self.load(metadata, data)

    def extract(self, input_: PipelineInputType) -> tuple[ProcessDataType, ProcessDataType]:
        return self._extraction_engine.extract(input_)

    def transform(self, data: ProcessDataType) -> ProcessDataType:
        data = self._transformation_engine.select_required(data)
        data = self._transformation_engine.drop_duplicates(data)
        data = self._transformation_engine.extract_remote(data)
        data = self._transformation_engine.extract_locations(data)
        data = self._transformation_engine.extract_contract_type(data)
        data = self._transformation_engine.extract_salaries(data)
        data = self._transformation_engine.unify_to_lower(data)
        data = self._transformation_engine.replace_values(data)
        data = self._transformation_engine.split_on_capitals(data)
        data = self._transformation_engine.to_title_case(data)
        data = self._transformation_engine.to_capitalized(data)
        data = self._transformation_engine.unify_missing_values(data)
        return data

    def load(self, metadata: ProcessDataType, data: ProcessDataType):
        self._loading_engine.load_tables_to_warehouse(metadata, data)


class PandasEtlExtractionFromJsonStr(EtlExtractionEngine[str, pd.DataFrame]):
    def __init__(self):
        pass

    def extract(self, input_: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Extract job postings data from JSON str to dataframes.

        The input JSON should have keys:
            'metadata': Json dump of 'PostingsMetadata' with keys:
                'source_name': Name of the data source.
                'obtained_datetime': Timestamp in format 'YYYY-MM-DD HH:MM:SS'.
            'raw_data': Raw data in format of a JSON string.
        """
        data = NoFluffJObsPostingsData.from_json_str(input_)
        self.validate_nofluffjobs_data(data)
        metadata_df = pd.DataFrame(dataclasses.asdict(data.metadata), index=[0])
        data_df = pd.DataFrame(data.raw_data['postings'])
        return metadata_df, data_df

    @staticmethod
    def validate_nofluffjobs_data(data: NoFluffJObsPostingsData):
        if data.metadata.source_name != 'nofluffjobs':
            raise ValueError(
                'Data extractor got correct data format type, but the '
                'metadata indicates invlaid data source; expected: '
                f'"nofluffjobs", got: {data.metadata.source_name}'
            )
        try:
            assert data.raw_data['totalCount'] == len(data.raw_data['postings'])
        except KeyError as error:
            raise ValueError(
                'Data extractor got correct date format type and '
                'metadata, but "raw_data" was malformed'
            ) from error


class PandasEtlTransformationEngine(EtlTransformationEngine[pd.DataFrame]):
    def __init__(self):
        self._geolocator = Geolocator(country_filter=EtlTransformationEngine.COUNTRY_FILTERS)

    def select_required(self, data: pd.DataFrame) -> pd.DataFrame:
        return data[self.COLS_TO_KEEP]

    def drop_duplicates(self, data: pd.DataFrame) -> pd.DataFrame:
        return data.drop_duplicates(subset=self.COLS_UNIQUE_IDENTITY)

    def unify_to_lower(self, data: pd.DataFrame) -> pd.DataFrame:
        for col in self.COLS_TO_LOWER:
            data[col] = data[col].str.lower().str.strip()
        return data

    def replace_values(self, data: pd.DataFrame) -> pd.DataFrame:
        for col in self.VALS_TO_REPLACE:
            data[col] = data[col].replace(to_replace=self.VALS_TO_REPLACE[col])
        return data

    def split_on_capitals(self, data: pd.DataFrame) -> pd.DataFrame:
        for col in EtlTransformationEngine.COLS_TO_SPLIT_ON_CAPITAL_LETTERS:
            data[col] = data[col].str.replace(r'(\w)([A-Z])', r'\1 \2', regex=True)
        return data

    def to_title_case(self, data: pd.DataFrame) -> pd.DataFrame:
        for col in EtlTransformationEngine.COLS_TO_TITLE_CASE:
            data[col] = data[col].str.title()
        return data

    def to_capitalized(self, data: pd.DataFrame) -> pd.DataFrame:
        specials = EtlTransformationEngine.CAPITALIZE_SPECIAL_NAMES
        for col in EtlTransformationEngine.COLS_TO_CAPITALIZE:
            data[col] = data[col][data[col].notna()].transform(
                lambda s: (specials[col][s] if s in specials[col] else s.capitalize())
            )
        return data

    def extract_remote(self, data: pd.DataFrame) -> pd.DataFrame:
        data['remote'] = data['location'].transform(
            lambda location_dict: location_dict['fullyRemote']
        )
        return data

    def extract_locations(self, data: pd.DataFrame) -> pd.DataFrame:
        data['city'] = data['location'].transform(
            lambda loc_dict: [
                city
                for location in loc_dict['places']
                if 'city' in location and (city := self._geolocator(location['city'])) is not None
            ]
        )
        return data

    def extract_contract_type(self, data: pd.DataFrame) -> pd.DataFrame:
        data['contract_type'] = data['salary'].transform(lambda salary_dict: salary_dict['type'])
        return data

    def extract_salaries(self, data: pd.DataFrame) -> pd.DataFrame:
        data['salary_min'] = data['salary'].transform(lambda salary_dict: salary_dict['from'])
        data['salary_max'] = data['salary'].transform(lambda salary_dict: salary_dict['to'])
        data['salary_mean'] = data[['salary_max', 'salary_min']].mean(axis=1)

        data = data[
            data['salary'].transform(
                lambda salary_dict: salary_dict['currency'] == self.SALARY_CURRENCY
            )
        ]
        data = data[data['salary_mean'] > self.MIN_MEAN_SALARY]
        return data

    def unify_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.replace('', None)
        data = data.replace('NaN', None)
        data = data.replace('Nan', None)
        data = data.replace('nan', None)
        data = data.replace(float('nan'), None)
        return data


class PandasEtlMongodbLoadingEngine(EtlLoadingEngine[pd.DataFrame]):
    def __init__(self, user_name: str, password: str, host: str, db_name: str, port=27017):
        self._db_client: MongoClient = MongoClient(
            host, port, username=user_name, password=password
        )
        self._db = self._db_client[db_name]

    @classmethod
    def from_config_file(cls, config_path: Path) -> 'PandasEtlMongodbLoadingEngine':
        return cls(**load_yaml_as_dict(config_path))

    def setup_warehouse(self):
        if 'metadata' not in self._db.list_collection_names():
            self._db.create_collection('metadata', validator={'$jsonSchema': METADATA_JSON_SCEHMA})
        if 'postings' not in self._db.list_collection_names():
            self._db.create_collection('postings', validator={"$jsonSchema": POSTINGS_JSON_SCHEMA})

    def load_tables_to_warehouse(self, metadata: pd.DataFrame, data: pd.DataFrame):
        self.setup_warehouse()
        batch_id = str(uuid.uuid4())

        metadata['batch_id'] = batch_id
        metadata_doc = metadata.to_dict('records')[0]
        self._db['metadata'].insert_one(metadata_doc)

        data['batch_id'] = batch_id
        postings_docs = data.to_dict('records')
        self._db['postings'].insert_many(postings_docs)


class PandasEtlSqlLoadingEngine(EtlLoadingEngine[pd.DataFrame]):
    POSTINGS_TABLE_COLS = [
        'name',
        'posted',
        'title',
        'technology',
        'category',
        'remote',
    ]

    SALARIES_TABLE_COLS = [
        'contract_type',
        'salary_min',
        'salary_max',
        'salary_mean',
    ]

    LOCATIONS_TABLE_COLS = ['city', 'lat', 'lon']

    SENIORITY_TABLE_COLS = ['seniority']

    def __init__(self, user_name: str, password: str, host: str, db_name: str, port=3306):
        self._db_con = db.create_engine(
            f'mysql+pymysql://{user_name}:{password}@{host}:{port}/{db_name}'
        )

    @classmethod
    def from_config_file(cls, config_file_path: Path) -> 'PandasEtlSqlLoadingEngine':
        return cls(**load_yaml_as_dict(config_file_path))

    def load_tables_to_warehouse(self, metadata: pd.DataFrame, data: pd.DataFrame):
        metadata.to_sql('metadata', con=self._db_con, if_exists='replace')

        postings_df = self.prepare_postings_table(data)
        postings_df.to_sql('postings', con=self._db_con, if_exists='replace')

        salaries_df = self.prepare_salaries_table(data)
        salaries_df.to_sql('salaries', con=self._db_con, if_exists='replace')

        location_df = self.prepare_locations_table(data)
        location_df.to_sql('locations', con=self._db_con, if_exists='replace')

        seniority_df = self.prepare_seniorities_table(data)
        seniority_df.to_sql('seniorities', con=self._db_con, if_exists='replace')

    def prepare_postings_table(self, data: pd.DataFrame) -> pd.DataFrame:
        postings_df = data[PandasEtlSqlLoadingEngine.POSTINGS_TABLE_COLS].reset_index()
        return Schemas.postings.validate(postings_df)

    def prepare_salaries_table(self, data: pd.DataFrame) -> pd.DataFrame:
        salaries_df = data[PandasEtlSqlLoadingEngine.SALARIES_TABLE_COLS].reset_index()
        return Schemas.salaries.validate(salaries_df)

    def prepare_locations_table(self, data: pd.DataFrame) -> pd.DataFrame:
        locations_df = data.explode('city')
        locations_df[['city', 'lat', 'lon']] = locations_df['city'].transform(
            lambda city: pd.Series([city[0], city[1], city[2]])
        )
        locations_df = locations_df[PandasEtlSqlLoadingEngine.LOCATIONS_TABLE_COLS]
        locations_df = locations_df.dropna().reset_index()
        return Schemas.locations.validate(locations_df)

    def prepare_seniorities_table(self, data: pd.DataFrame) -> pd.DataFrame:
        seniority_df = data.explode('seniority')
        seniority_df = seniority_df[PandasEtlSqlLoadingEngine.SENIORITY_TABLE_COLS].reset_index()
        return Schemas.seniorities.validate(seniority_df)


class EtlLoaderImpl(Enum):
    MONGODB = auto()
    SQL = auto()


class EtlLoaderFactory:
    def __init__(self, impl_type: EtlLoaderImpl, config_path: Path):
        self._impl_type = impl_type
        self._config_path = config_path

    def make(self) -> EtlLoadingEngine:
        match self._impl_type:
            case EtlLoaderImpl.MONGODB:
                return PandasEtlMongodbLoadingEngine.from_config_file(self._config_path)
            case EtlLoaderImpl.SQL:
                return PandasEtlSqlLoadingEngine.from_config_file(self._config_path)
            case _:
                raise ValueError('Selected ETL loader implementation is not supported or invalid')
