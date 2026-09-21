import argparse
import logging
from pathlib import Path

import pandas as pd


REQUIRED_FILES = [{"id": "sap", "cli_argument": "--sap", "argument_name": "sap"}, {"id": "billing", "cli_argument": "--billing", "argument_name": "billing"}]
OUTPUTS = ["conciliacao.xlsx", "divergencias.xlsx"]
OUTPUT_FOLDER = 'data/output'
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def read_input(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, sep=";")
    return pd.read_excel(path)


def reconcile(left: pd.DataFrame, right: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    common_columns = [column for column in left.columns if column in right.columns]
    if not common_columns:
        raise ValueError("Nenhuma coluna comum encontrada para a conciliacao.")
    merged = left.merge(right, on=common_columns, how="outer", indicator=True, suffixes=("_sap", "_billing"))
    matched = merged[merged["_merge"] == "both"].drop(columns=["_merge"])
    divergences = merged[merged["_merge"] != "both"].drop(columns=["_merge"])
    return matched, divergences


def main() -> None:
    parser = argparse.ArgumentParser(description='Conciliacao SAP x Billing')
    for required_file in REQUIRED_FILES:
        parser.add_argument(required_file["cli_argument"], required=True)
    args = parser.parse_args()

    frames = [read_input(getattr(args, item["argument_name"])) for item in REQUIRED_FILES]
    if len(frames) < 2:
        raise ValueError("O padrao de conciliacao exige pelo menos dois inputs.")

    conciliados, divergencias = reconcile(frames[0], frames[1])
    output_folder = Path(OUTPUT_FOLDER)
    output_folder.mkdir(parents=True, exist_ok=True)
    output_map = {
        "conciliacao.xlsx": conciliados,
        "divergencias.xlsx": divergencias,
    }
    for output_name in OUTPUTS:
        output_map.get(output_name, divergencias).to_excel(output_folder / output_name, index=False)
    logger.info("Conciliacao base concluida: %s", 'conciliacao_sap_billing')
    # TODO: implementar regras de negocio, chaves e classificacoes especificas.


if __name__ == "__main__":
    main()
