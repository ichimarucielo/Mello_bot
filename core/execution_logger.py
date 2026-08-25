import json

from pathlib import Path
from datetime import datetime


class ExecutionLogger:

    LOG_FOLDER = Path("logs")

    @classmethod
    def ensure_folder(cls) -> None:

        cls.LOG_FOLDER.mkdir(
            parents=True,
            exist_ok=True
        )

    @classmethod
    def save(
        cls,
        payload: dict
    ) -> None:

        cls.ensure_folder()

        execution_id = payload[
            "execution_id"
        ]

        log_file = (
            cls.LOG_FOLDER
            / f"{execution_id}.json"
        )

        with open(
            log_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=4
            )

    @classmethod
    def create_execution_id(
        cls
    ) -> str:

        return datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )