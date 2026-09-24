import argparse
import logging
from pathlib import Path

import pandas as pd


REQUIRED_FILES = [{'id': 'zsd008_antigo', 'cli_argument': '--zsd008-antigo', 'argument_name': 'zsd008_antigo'}, {'id': 'zsd008_novo', 'cli_argument': '--zsd008-novo', 'argument_name': 'zsd008_novo'}]
OUTPUTS = ['comparação_mes_zsd008.xlsx']
OUTPUT_MODE = 'workbook'
WORKBOOK_SHEETS = ['comparação_mes_zsd008.xlsx']
PIPELINE_STEPS = [{'operation': 'normalize', 'description': '', 'parameters': {'key': None, 'group_by': None, 'sum': None, 'collect': None, 'column': None, 'descending': None}}, {'operation': 'deduplicate', 'description': '', 'parameters': {'key': 'Número da Nota Fiscal', 'group_by': None, 'sum': None, 'collect': None, 'column': None, 'descending': None}}, {'operation': 'aggregate', 'description': '', 'parameters': {'key': None, 'group_by': 'Número da Nota Fiscal', 'sum': ['Valor Bruto', 'Qtde Transação'], 'collect': 'Discriminação', 'column': None, 'descending': None}}, {'operation': 'reconcile', 'description': '', 'parameters': {'key': 'Número da Nota Fiscal', 'group_by': None, 'sum': None, 'collect': None, 'column': None, 'descending': None}}, {'operation': 'aggregate', 'description': '', 'parameters': {'key': None, 'group_by': 'Razão Social', 'sum': None, 'collect': None, 'column': None, 'descending': None}}, {'operation': 'sort', 'description': '', 'parameters': {'key': None, 'group_by': None, 'sum': None, 'collect': None, 'column': 'saldo_liquido', 'descending': True}}]
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
    parser = argparse.ArgumentParser(description='Comparacao ZSD008 entre Periodos')
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
    logger.info("Conciliacao base concluida: %s", 'comparacao_zsd008_periodos')
    # TODO: implementar regras de negocio, chaves e classificacoes especificas.


if __name__ == "__main__":
    main()
