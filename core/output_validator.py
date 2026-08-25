from pathlib import Path


class OutputValidator:

    @staticmethod
    def validate(
        output_folder: Path,
        expected_outputs: list[str]
    ) -> dict:

        found = []

        missing = []

        for output_file in expected_outputs:

            file_path = (
                output_folder /
                output_file
            )

            if file_path.exists():

                found.append(
                    {
                        "name": output_file,
                        "path": file_path
                    }
                )

            else:

                missing.append(
                    output_file
                )

        return {
            "valid": len(missing) == 0,
            "found": found,
            "missing": missing
        }