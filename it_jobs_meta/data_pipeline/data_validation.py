"""Data validation schemas for postings data."""

from dataclasses import dataclass
from datetime import datetime

import pandera as pa

# SQL schemas


@dataclass
class Schemas:
    postings = pa.DataFrameSchema(
        {
            'id': pa.Column(str, unique=True),
            'name': pa.Column(str, nullable=True),
            'posted': pa.Column(datetime, coerce=True, nullable=True),
            'title': pa.Column(str, nullable=True),
            'technology': pa.Column(str, nullable=True),
            'category': pa.Column(str, nullable=True),
            'url': pa.Column(str, nullable=True),
            'remote': pa.Column(bool, coerce=True),
        }
    )

    salaries = pa.DataFrameSchema(
        {
            'id': pa.Column(str, unique=True),
            'contract_type': pa.Column(str),
            'salary_min': pa.Column(float, pa.Check.ge(0), coerce=True),
            'salary_max': pa.Column(float, pa.Check.ge(0), coerce=True),
            'salary_mean': pa.Column(float, pa.Check.ge(0), coerce=True),
        }
    )

    locations = pa.DataFrameSchema(
        {
            'id': pa.Column(str),
            'city': pa.Column(str),
            'lat': pa.Column(
                float, pa.Check.ge(-90), pa.Check.le(90), coerce=True  # type: ignore # noqa: e510
            ),
            'lon': pa.Column(
                float, pa.Check.ge(-180), pa.Check.le(180), coerce=True  # type: ignore # noqa: e501
            ),
        }
    )

    seniorities = pa.DataFrameSchema({'id': pa.Column(str), 'seniority': pa.Column(str)})


# NoSQL schemas


METADATA_JSON_SCEHMA = {
    "bsonType": "object",
    "required": ["source_name", "obtained_datetime", "batch_id"],
    "properties": {
        "source_name": {"bsonType": "string"},
        "obtained_datetime": {"bsonType": "date"},
        "batch_id": {"bsonType": "string"},
    },
}


POSTINGS_JSON_SCHEMA = {
    "bsonType": "object",
    "required": [
        "name",
        "posted",
        "title",
        "technology",
        "category",
        "remote",
        "contract_type",
        "salary_min",
        "salary_max",
        "salary_mean",
        "city",
        "seniority",
        "batch_id",
    ],
    "properties": {
        "name": {"bsonType": "string"},
        "posted": {"bsonType": "long"},
        "title": {"bsonType": "string"},
        "technology": {"bsonType": ["string", "null"]},
        "category": {"bsonType": "string"},
        "remote": {"bsonType": "bool"},
        "contract_type": {"bsonType": "string"},
        "salary_min": {"bsonType": ["double", "int"]},
        "salary_max": {"bsonType": ["double", "int"]},
        "salary_mean": {"bsonType": ["double", "int"]},
        "city": {
            "bsonType": "array",
            "items": {
                "bsonType": "array",
                # City name, latitude, longitude
                "items": [
                    {"bsonType": "string"},
                    {"bsonType": ["double", "int"]},
                    {"bsonType": ["double", "int"]},
                ],
            },
        },
        "seniority": {"bsonType": "array", "items": {"bsonType": "string"}},
        "batch_id": {"bsonType": "string"},
    },
}
