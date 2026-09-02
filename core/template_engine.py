import json

from core.models import Manifest


class TemplateEngine:

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
