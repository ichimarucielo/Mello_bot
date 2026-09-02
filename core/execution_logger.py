import json
from datetime import datetime
from core.models import ExecutionResult
from core.settings import LOGS_DIR


class ExecutionLogger:

    LOG_FOLDER = LOGS_DIR

    @classmethod
    def ensure_folder(cls) -> None:

        cls.LOG_FOLDER.mkdir(
            parents=True,
            exist_ok=True
        )

    @classmethod
    def save(
        cls,
        payload: ExecutionResult | dict,
    ) -> None:

        cls.ensure_folder()

        if isinstance(
            payload,
            ExecutionResult,
        ):
            payload = payload.model_dump(
                mode="json"
            )

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
            encoding="utf-8",
        ) as file:

            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=4,
            )

    @classmethod
    def create_execution_id(
        cls
    ) -> str:

        return datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )