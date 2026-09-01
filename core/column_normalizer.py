import re
import unicodedata


def normalize_column(column: str) -> str:
    column = column.strip().lower()

    column = unicodedata.normalize(
        "NFKD",
        column,
    )

    column = "".join(
        char
        for char in column
        if not unicodedata.combining(char)
    )

    column = re.sub(r"\s+", " ", column)

    return column.strip()