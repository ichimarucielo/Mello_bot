import requests

url = (
    "http://127.0.0.1:8000"
    "/projects/ia_quarteto/run"
)

files = [
    (
        "files",
        (
            "prefeitura.csv",
            open(
                r"C:\dev\mello_bot\inputs\ia_quarteto\prefeitura.csv",
                "rb"
            ),
            "text/csv",
        ),
    ),
    (
        "files",
        (
            "fs10n.xlsx",
            open(
                r"C:\dev\mello_bot\inputs\ia_quarteto\fs10n.xlsx",
                "rb"
            ),
            "application/octet-stream",
        ),
    ),
    (
        "files",
        (
            "zsd008.xlsx",
            open(
                r"C:\dev\mello_bot\inputs\ia_quarteto\zsd008.xlsx",
                "rb"
            ),
            "application/octet-stream",
        ),
    ),
]

response = requests.post(
    url,
    files=files,
)

print(response.status_code)
print(response.json())