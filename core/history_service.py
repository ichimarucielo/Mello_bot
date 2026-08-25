import json

from pathlib import Path


class HistoryService:

    LOG_FOLDER = Path("logs")

    @classmethod
    def get_history(
        cls,
        limit: int = 10
    ) -> list:

        if not cls.LOG_FOLDER.exists():

            return []

        executions = []

        for log_file in cls.LOG_FOLDER.glob(
            "*.json"
        ):

            try:

                with open(
                    log_file,
                    "r",
                    encoding="utf-8"
                ) as file:

                    executions.append(
                        json.load(file)
                    )

            except Exception:

                continue

        executions.sort(
            key=lambda x: x.get(
                "start_time",
                ""
            ),
            reverse=True
        )

        return executions[:limit]