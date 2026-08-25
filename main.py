from pathlib import Path

from core.identifier import Identifier


def main():

    result = Identifier.identify(
        Path(
            r"C:\dev\IA_QUARTETO\data\raw\prefeitura\469741F8A1JUL2026.csv"
        )
    )

    print(result)


if __name__ == "__main__":
    main()