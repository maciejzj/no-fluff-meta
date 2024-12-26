from pathlib import Path

from it_jobs_meta.data_pipeline.data_ingestion import (
    NoFluffJobsPostingsDataSource,
)


def main():
    data_source = NoFluffJobsPostingsDataSource()
    data = data_source.get()
    data_key = data.make_key_for_data()
    json_data_string = data.make_json_str_from_data()
    output_path = Path(f'data_processing/test/{data_key}.json')

    with open(output_path, 'w', encoding='utf-8') as text_file:
        text_file.write(json_data_string)


if __name__ == '__main__':
    main()
