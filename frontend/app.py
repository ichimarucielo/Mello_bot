import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT))

import streamlit as st

from core.execution_logger import (
    ExecutionLogger
)

from core.history_service import (
    HistoryService
)

from core.registry import load_projects
from core.executor import Executor
from core.file_manager import FileManager
from core.validator import Validator
from core.output_validator import OutputValidator
from core.identifier import (
    Identifier
)

def validate_uploaded_files(
    project_id: str,
    project: dict,
    uploaded_files: dict
) -> tuple[list, bool]:

    validation_results = []

    all_valid = True

    for file_definition in project["required_files"]:

        file_id = file_definition["id"]

        uploaded_file = uploaded_files.get(
            file_id
        )

        if uploaded_file is None:

            all_valid = False

            continue

        saved_file = (
            FileManager.save_uploaded_file(
                project_id=project_id,
                file_id=file_id,
                uploaded_file=uploaded_file
            )
        )

        result = Validator.validate_file(
            file_path=saved_file,
            file_definition=file_definition
        )

        validation_results.append(
            result
        )

        if not result["valid"]:

            all_valid = False

    return (
        validation_results,
        all_valid
    )


st.set_page_config(
    page_title="MELLO BOT",
    page_icon="🤖",
    layout="wide"
)

FileManager.ensure_folders()

st.title("🤖 MELLO BOT")

with st.sidebar:

    st.header(
        "📋 Histórico"
    )

    history = (
        HistoryService.get_history()
    )

    if not history:

        st.info(
            "Nenhuma execução encontrada."
        )

    else:

        for execution in history:

            status = (
                "✅"
                if execution["status"] == "success"
                else "❌"
            )

            duration = execution.get(
                "duration_seconds",
                "-"
            )

            st.markdown(
                f"""
{status} **{execution['project_id']}**

Tempo: {duration}s

Execução:
{execution['execution_id']}
"""
            )

            st.divider()

projects = load_projects()

selected_project_id = st.selectbox(
    "Selecione um ETL",
    options=list(projects.keys()),
    format_func=lambda x: projects[x]["name"]
)

project = projects[
    selected_project_id
]

st.subheader(
    project["name"]
)

st.write(
    project["description"]
)

st.divider()

st.subheader(
    "Arquivos obrigatórios"
)

uploaded_files = {}

for file_definition in project[
    "required_files"
]:

    uploaded_file = st.file_uploader(
        label=file_definition[
            "display_name"
        ],
        type=file_definition[
            "accepted_extensions"
        ],
        key=file_definition["id"]
    )

    uploaded_files[
        file_definition["id"]
    ] = uploaded_file

st.divider()

all_files_uploaded = all(
    uploaded_files.values()
)

validation_results = []

all_files_valid = False

if not all_files_uploaded:

    st.warning(
        "Envie todos os arquivos obrigatórios."
    )

else:

    (
        validation_results,
        all_files_valid
    ) = validate_uploaded_files(
        project_id=selected_project_id,
        project=project,
        uploaded_files=uploaded_files
    )

    st.subheader(
        "Validação"
    )

    for result in validation_results:

        if result["valid"]:

            st.success(
                f"{result['display_name']} - Score: {result['score']}%"
            )

        else:

            st.error(
                f"{result['display_name']} - Score: {result['score']}%"
            )

            if result["missing_columns"]:

                st.write(
                    "Colunas ausentes:"
                )

                for column in result[
                    "missing_columns"
                ]:

                    st.write(
                        f"• {column}"
                    )

    if all_files_valid:

        st.success(
            "Todos os arquivos foram validados."
        )

    else:

        st.error(
            "Existem erros de validação."
        )

st.divider()

if st.button(
    "Executar ETL",
    disabled=not all_files_valid
):

    execution_id = (
        ExecutionLogger
        .create_execution_id()
    )

    start_time = datetime.now()

    try:

        with st.spinner(
            "Executando ETL..."
        ):

            Executor.run(
                selected_project_id
            )

        output_result = (
            OutputValidator.validate(
                output_folder=Path(
                    r"C:\dev\Ia_quarteto\data\output"
                ),
                expected_outputs=project[
                    "outputs"
                ]
            )
        )

        st.session_state[
            "output_result"
        ] = output_result

        end_time = datetime.now()

        ExecutionLogger.save(
            {
                "execution_id": execution_id,
                "project_id": selected_project_id,
                "project_name": project[
                    "name"
                ],
                "status": "success",
                "start_time": (
                    start_time.isoformat()
                ),
                "end_time": (
                    end_time.isoformat()
                ),
                "duration_seconds": round(
                    (
                        end_time
                        - start_time
                    ).total_seconds(),
                    2
                ),
                "outputs": [
                    file_info["name"]
                    for file_info in output_result[
                        "found"
                    ]
                ]
            }
        )

        st.success(
            "ETL executado com sucesso!"
        )

    except Exception as error:

        ExecutionLogger.save(
            {
                "execution_id": execution_id,
                "project_id": selected_project_id,
                "project_name": project[
                    "name"
                ],
                "status": "error",
                "error": str(error)
            }
        )

        st.error(
            str(error)
        )

if "output_result" in st.session_state:

    output_result = (
        st.session_state[
            "output_result"
        ]
    )

    st.divider()

    st.subheader(
        "Arquivos Gerados"
    )

    for file_info in output_result[
        "found"
    ]:

        st.success(
            file_info["name"]
        )

        with open(
            file_info["path"],
            "rb"
        ) as file:

            st.download_button(
                label=(
                    f"📥 Baixar "
                    f"{file_info['name']}"
                ),
                data=file.read(),
                file_name=file_info[
                    "name"
                ],
                mime=(
                    "application/"
                    "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                key=f"download_{file_info['name']}"
            )

    if output_result["missing"]:

        st.error(
            "Arquivos não encontrados:"
        )

        for missing_file in output_result[
            "missing"
        ]:

            st.write(
                f"• {missing_file}"
            )