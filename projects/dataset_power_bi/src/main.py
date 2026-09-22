import argparse
import logging
from pathlib import Path

import pandas as pd


REQUIRED_FILES = [{"id": "origem", "cli_argument": "--input-file", "argument_name": "input_file"}]
OUTPUTS = ["dataset.csv"]
OUTPUT_FOLDER = 'data/output'
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def read_input(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, sep=";")
    return pd.read_excel(path)


def main() -> None:
    parser = argparse.ArgumentParser(description='Dataset Power BI')
    for required_file in REQUIRED_FILES:
        parser.add_argument(required_file["cli_argument"], required=True)
    args = parser.parse_args()
    data = read_input(getattr(args, REQUIRED_FILES[0]["argument_name"]))

    # TODO: aplicar limpeza, tipagem e regras do dataset.
    output_folder = Path(OUTPUT_FOLDER)
    output_folder.mkdir(parents=True, exist_ok=True)
    for output_name in OUTPUTS:
        data.to_csv(output_folder / output_name, index=False)
    logger.info("Dataset Power BI exportado: %s", 'dataset_power_bi')


if __name__ == "__main__":
    main()
