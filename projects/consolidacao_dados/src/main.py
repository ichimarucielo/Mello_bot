import argparse
import logging
from pathlib import Path

import pandas as pd


REQUIRED_FILES = [{"id": "entrada", "cli_argument": "--input-file", "argument_name": "input_file"}]
OUTPUTS = ["consolidado.xlsx"]
OUTPUT_FOLDER = 'data/output'
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def read_input(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, sep=";")
    return pd.read_excel(path)


def main() -> None:
    parser = argparse.ArgumentParser(description='Consolidacao Dados')
    for required_file in REQUIRED_FILES:
        parser.add_argument(required_file["cli_argument"], required=True)
    args = parser.parse_args()
    frames = [read_input(getattr(args, item["argument_name"])) for item in REQUIRED_FILES]
    consolidated = pd.concat(frames, ignore_index=True)

    output_folder = Path(OUTPUT_FOLDER)
    output_folder.mkdir(parents=True, exist_ok=True)
    for output_name in OUTPUTS:
        consolidated.to_excel(output_folder / output_name, index=False)
    logger.info("Consolidacao concluida: %s", 'consolidacao_dados')


if __name__ == "__main__":
    main()
