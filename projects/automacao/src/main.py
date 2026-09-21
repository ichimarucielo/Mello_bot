import argparse
import logging
from pathlib import Path


REQUIRED_FILES = [{"id": "faturamento", "cli_argument": "--faturamento"}, {"id": "sap", "cli_argument": "--sap"}]

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description='Automacao Gerada')
    for required_file in REQUIRED_FILES:
        parser.add_argument(required_file["cli_argument"], required=True)
    args = parser.parse_args()

    input_paths = {
        required_file["id"]: Path(getattr(
            args,
            required_file["cli_argument"].lstrip("-").replace("-", "_"),
        ))
        for required_file in REQUIRED_FILES
    }
    for file_id, input_path in input_paths.items():
        if not input_path.is_file():
            raise FileNotFoundError(f"Input {file_id} nao encontrado: {input_path}")
        logger.info("Input recebido: %s", input_path)

    # TODO: implementar a regra de negocio da automacao.
    # TODO: gerar os outputs declarados no manifesto.
    logger.info("Scaffold pronto para implementacao: %s", 'automacao')


if __name__ == "__main__":
    main()
