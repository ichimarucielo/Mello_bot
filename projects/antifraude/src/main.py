import argparse
import logging
from pathlib import Path

import pandas as pd


REQUIRED_FILES = [{'id': 'fbl5n_aberta', 'cli_argument': '--fbl5n-aberta', 'argument_name': 'fbl5n_aberta'}, {'id': 'fbl5n_compensada', 'cli_argument': '--fbl5n-compensada', 'argument_name': 'fbl5n_compensada'}]
OUTPUTS = ['fbl5nConciliação.xlsx']
OUTPUT_MODE = 'workbook'
WORKBOOK_SHEETS = ['fbl5nConciliação.xlsx']
PIPELINE_STEPS = [{'operation': 'normalize', 'description': '', 'parameters': {'key': None}}, {'operation': 'reconcile', 'description': '', 'parameters': {'key': 'documento'}}]
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
    merged = left.merge(right, on=common_columns, how="outer", indicator=True, suffixes=("_left", "_right"))
    matched = merged[merged["_merge"] == "both"].drop(columns=["_merge"])
    divergences = merged[merged["_merge"] != "both"].drop(columns=["_merge"])
    return matched, divergences


def main() -> None:
    parser = argparse.ArgumentParser(description='ComparaçãoFBL5N')
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
    if OUTPUT_MODE == "workbook":
        workbook_path = output_folder / OUTPUTS[0]
        with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
            for sheet_name in WORKBOOK_SHEETS:
                safe_sheet_name = str(sheet_name).replace(".xlsx", "")[:31] or "Resultado"
                frame = divergencias if "perd" in safe_sheet_name.lower() else conciliados
                frame.to_excel(writer, sheet_name=safe_sheet_name, index=False)
        logger.info("Workbook com abas gerado: %s", workbook_path)
        return
    for output_name in OUTPUTS:
        output_map.get(output_name, divergencias).to_excel(output_folder / output_name, index=False)
    logger.info("Conciliacao base concluida: %s", 'antifraude')
    # TODO: implementar regras de negocio, chaves e classificacoes especificas.


if __name__ == "__main__":
    main()
