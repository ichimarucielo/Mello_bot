import json
from pathlib import Path

import yaml

from core.models import Manifest


class TemplateEngine:

    TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

    TEMPLATE_FILES = {
        "generic": "generic_main.py.j2",
        "reconciliation": "reconciliation_main.py.j2",
        "consolidation": "consolidation_main.py.j2",
        "antifraud": "antifraud_main.py.j2",
        "powerbi": "powerbi_main.py.j2",
        "validation": "validation_main.py.j2",
    }

    @classmethod
    def render_pattern_main(cls, manifest: Manifest, pattern: str = "generic") -> str:
        template_name = cls.TEMPLATE_FILES.get(pattern, cls.TEMPLATE_FILES["generic"])
        template_path = cls.TEMPLATE_DIR / template_name
        template = template_path.read_text(encoding="utf-8")
        required_files = [
            {
                "id": required_file.id,
                "cli_argument": required_file.cli_argument,
                "argument_name": required_file.cli_argument.lstrip("-").replace("-", "_"),
            }
            for required_file in manifest.required_files
            if required_file.cli_argument
        ]
        replacements = {
            "{{ REQUIRED_FILES }}": json.dumps(required_files, ensure_ascii=False),
            "{{ OUTPUTS }}": json.dumps(manifest.outputs, ensure_ascii=False),
            "{{ OUTPUT_FOLDER }}": repr(getattr(manifest, "output_folder", "data/output")),
            "{{ PROJECT_NAME }}": repr(manifest.name),
            "{{ PROJECT_ID }}": repr(manifest.id),
            "{{ STEPS }}": json.dumps(manifest.steps, ensure_ascii=False),
        }
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)
        return template

    @staticmethod
    def render_manifest(manifest: Manifest) -> str:
        return yaml.safe_dump(
            manifest.model_dump(mode="json"),
            allow_unicode=True,
            sort_keys=False,
        )

    @staticmethod
    def render_main(manifest: Manifest) -> str:
        required_files = [
            {
                "id": required_file.id,
                "cli_argument": required_file.cli_argument,
            }
            for required_file in manifest.required_files
            if required_file.cli_argument
        ]

        return f'''import argparse
from pathlib import Path

import pandas as pd


REQUIRED_FILES = {json.dumps(required_files, ensure_ascii=False)}
OUTPUTS = {json.dumps(manifest.outputs, ensure_ascii=False)}
OUTPUT_FOLDER = {json.dumps(getattr(manifest, "output_folder", "data/output"), ensure_ascii=False)}


def read_input(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, sep=";")
    return pd.read_excel(path)


def main() -> None:
    parser = argparse.ArgumentParser(description={manifest.name!r})
    for required_file in REQUIRED_FILES:
        parser.add_argument(required_file["cli_argument"], required=True)
    args = parser.parse_args()

    frames = [
        read_input(getattr(args, required_file["cli_argument"].lstrip("-").replace("-", "_")))
        for required_file in REQUIRED_FILES
    ]
    result = frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)

    output_folder = Path(OUTPUT_FOLDER)
    output_folder.mkdir(parents=True, exist_ok=True)
    for output_name in OUTPUTS:
        result.to_excel(output_folder / output_name, index=False)

    print("Projeto criado executado com sucesso")


if __name__ == "__main__":
    main()
'''

    @staticmethod
    def render_designer_main(manifest: Manifest) -> str:
        arguments = [
            {
                "id": required_file.id,
                "cli_argument": required_file.cli_argument,
            }
            for required_file in manifest.required_files
            if required_file.cli_argument
        ]

        return f'''import argparse
import logging
from pathlib import Path


REQUIRED_FILES = {json.dumps(arguments, ensure_ascii=False)}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description={manifest.name!r})
    for required_file in REQUIRED_FILES:
        parser.add_argument(required_file["cli_argument"], required=True)
    args = parser.parse_args()

    input_paths = {{
        required_file["id"]: Path(getattr(
            args,
            required_file["cli_argument"].lstrip("-").replace("-", "_"),
        ))
        for required_file in REQUIRED_FILES
    }}
    for file_id, input_path in input_paths.items():
        if not input_path.is_file():
            raise FileNotFoundError(f"Input {{file_id}} nao encontrado: {{input_path}}")
        logger.info("Input recebido: %s", input_path)

    # TODO: implementar a regra de negocio da automacao.
    # TODO: gerar os outputs declarados no manifesto.
    logger.info("Scaffold pronto para implementacao: %s", {manifest.id!r})


if __name__ == "__main__":
    main()
'''

    @staticmethod
    def render_readme(manifest: Manifest) -> str:
        inputs = "\n".join(
            f"- `{item.id}`: {item.display_name} ({', '.join(item.accepted_extensions)})"
            for item in manifest.required_files
        )
        outputs = "\n".join(f"- `{output}`" for output in manifest.outputs)
        return f'''# {manifest.name}

## Objetivo

{manifest.description}

## Inputs

{inputs}

## Outputs

{outputs}

## Como executar

```bash
python {manifest.entrypoint.script} --help
```

Preencha os argumentos definidos no manifesto e execute o comando a partir da raiz deste projeto.

## Estrutura

```text
{manifest.entrypoint.script}
data/input/
data/output/
manifest.yaml
```

## Criterios de aceite

- os inputs devem ser validados conforme as colunas declaradas;
- a regra de negocio deve ser implementada no entrypoint;
- todos os outputs declarados devem ser gerados na pasta configurada;
- a execucao deve retornar codigo zero em caso de sucesso;
- o resultado deve ser revisado com dados reais antes de producao.

## Proximos passos de implementacao

- confirmar as colunas e chaves de negocio com os arquivos reais;
- substituir os TODOs pela regra especifica do ETL;
- revisar os nomes e a pasta dos outputs declarados no manifesto;
- adicionar testes com casos validos, divergentes e arquivos vazios;
- executar uma validacao end-to-end antes de publicar a automacao.
'''
