# test_upload.py

import requests

url = "http://127.0.0.1:8000/test-upload"

files = [
    (
        "files",
        (
            "prefeitura.csv",
            open(
                r"C:\dev\mello_bot\inputs\ia_quarteto\prefeitura.csv",
                "rb",
            ),
            "text/csv",
        ),
    ),
]

response = requests.post(
    url,
    files=files,
)

print(response.status_code)
print(response.text)