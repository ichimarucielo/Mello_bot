import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_FOLDER = ROOT / "data" / "output"

# =============================================================================
# IMPORTS
# =============================================================================

from core.execution_logger import ExecutionLogger
from core.executor import Executor
from core.file_manager import FileManager
from core.history_service import HistoryService
from core.output_validator import OutputValidator
from core.registry import load_projects
from core.validator import Validator

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="MELLO BOT",
    page_icon="🤖",
    layout="wide",
)

# =============================================================================
# HELPERS
# =============================================================================


def validate_uploaded_files(
    project_id: str,
    project: dict[str, Any],
    uploaded_files: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:

    validation_results = []
    all_valid = True

    for file_definition in project.get("required_files", []):

        file_id = file_definition["id"]

        uploaded_file = uploaded_files.get(file_id)

        if uploaded_file is None:
            all_valid = False
            continue

        try:

            saved_file = FileManager.save_uploaded_file(
                project_id=project_id,
                file_id=file_id,
                uploaded_file=uploaded_file,
            )

            result = Validator.validate_file(
                file_path=saved_file,
                file_definition=file_definition,
            )

            validation_results.append(result)

            if not result.get("valid", False):
                all_valid = False

        except Exception:

            logger.exception(
                "Erro validando arquivo %s",
                file_id,
            )

            validation_results.append(
                {
                    "file_id": file_id,
                    "display_name": file_definition.get(
                        "display_name",
                        file_id,
                    ),
                    "valid": False,
                    "score": 0,
                    "missing_columns": [],
                    "error": "Erro ao processar arquivo",
                }
            )

            all_valid = False

    return validation_results, all_valid


# =============================================================================
# FILE MANAGER INIT
# =============================================================================

FileManager.ensure_folders()

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:

    st.header("📋 Histórico")

    try:

        history = HistoryService.get_history()

    except Exception:

        logger.exception(
            "Erro carregando histórico"
        )

        history = []

    if not history:

        st.info(
            "Nenhuma execução encontrada."
        )

    else:

        for execution in history[-30:]:

            status_icon = (
                "✅"
                if execution.get("status")
                == "success"
                else "❌"
            )

            st.markdown(
                f"""
{status_icon} **{execution.get('project_id', '-') }**

Tempo: {execution.get('duration_seconds', '-') }s

Execução: `{execution.get('execution_id', '-')}`
"""
            )

            st.divider()

# =============================================================================
# MAIN
# =============================================================================

st.title("🤖 MELLO BOT")

projects = load_projects()

selected_project_id = st.selectbox(
    "Selecione um ETL",
    options=list(projects.keys()),
    format_func=lambda x: projects[x]["name"],
)

project = projects[selected_project_id]

st.subheader(project["name"])
st.write(project["description"])

st.divider()

# =============================================================================
# UPLOADS
# =============================================================================

st.subheader(
    "Arquivos obrigatórios"
)

uploaded_files = {}

for file_definition in project.get(
    "required_files",
    [],
):

    uploaded_files[
        file_definition["id"]
    ] = st.file_uploader(
        label=file_definition[
            "display_name"
        ],
        type=file_definition[
            "accepted_extensions"
        ],
        key=file_definition["id"],
    )

st.divider()

all_files_uploaded = all(
    uploaded_files.values()
)

validation_results = []
all_files_valid = False

# =============================================================================
# VALIDATION
# =============================================================================

if not all_files_uploaded:

    st.warning(
        "Envie todos os arquivos obrigatórios."
    )

else:

    (
        validation_results,
        all_files_valid,
    ) = validate_uploaded_files(
        project_id=selected_project_id,
        project=project,
        uploaded_files=uploaded_files,
    )

    st.subheader("Validação")

    for result in validation_results:

        display_name = result.get(
            "display_name",
            "Arquivo",
        )

        score = result.get(
            "score",
            0,
        )

        if result.get(
            "valid",
            False,
        ):

            st.success(
                f"{display_name} - Score: {score}%"
            )

        else:

            st.error(
                f"{display_name} - Score: {score}%"
            )

            missing_columns = result.get(
                "missing_columns",
                [],
            )

            if missing_columns:

                st.write(
                    "Colunas ausentes:"
                )

                for column in missing_columns:

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

# =============================================================================
# EXECUÇÃO
# =============================================================================

st.divider()

if st.button(
    "Executar ETL",
    disabled=not all_files_valid,
):

    execution_id = (
        ExecutionLogger.create_execution_id()
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
                output_folder=OUTPUT_FOLDER,
                expected_outputs=project.get(
                    "outputs",
                    [],
                ),
            )
        )

        st.session_state[
            "output_result"
        ] = output_result

        st.session_state[
            "output_project_id"
        ] = selected_project_id

        end_time = datetime.now()

        found = output_result.get(
            "found",
            [],
        )

        missing = output_result.get(
            "missing",
            [],
        )

        status = (
            "success"
            if not missing
            else "partial_success"
        )

        ExecutionLogger.save(
            {
                "execution_id": execution_id,
                "project_id": selected_project_id,
                "project_name": project["name"],
                "status": status,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": round(
                    (
                        end_time
                        - start_time
                    ).total_seconds(),
                    2,
                ),
                "outputs": [
                    x["name"]
                    for x in found
                ],
                "missing_outputs": missing,
            }
        )

        st.success(
            "ETL executado com sucesso!"
        )

    except Exception as error:

        logger.exception(
            "Erro executando ETL"
        )

        ExecutionLogger.save(
            {
                "execution_id": execution_id,
                "project_id": selected_project_id,
                "project_name": project["name"],
                "status": "error",
                "error": str(error),
            }
        )

        st.error(
            f"Erro ao executar ETL: {error}"
        )

# =============================================================================
# OUTPUTS
# =============================================================================

if (
    "output_result"
    in st.session_state
):

    if (
        st.session_state.get(
            "output_project_id"
        )
        == selected_project_id
    ):

        output_result = (
            st.session_state[
                "output_result"
            ]
        )

        st.divider()

        st.subheader(
            "Arquivos Gerados"
        )

        for file_info in output_result.get(
            "found",
            [],
        ):

            file_path = Path(
                file_info["path"]
            )

            if not file_path.exists():

                st.error(
                    f"Arquivo não encontrado: {file_info['name']}"
                )

                continue

            st.success(
                file_info["name"]
            )

            try:

                file_data = (
                    file_path.read_bytes()
                )

            except OSError:

                logger.exception(
                    "Erro lendo arquivo %s",
                    file_path,
                )

                st.error(
                    f"Erro ao ler {file_info['name']}"
                )

                continue

            st.download_button(
                label=f"📥 Baixar {file_info['name']}",
                data=file_data,
                file_name=file_info[
                    "name"
                ],
                key=f"download_{file_info['name']}",
            )

        missing = output_result.get(
            "missing",
            [],
        )

        if missing:

            st.error(
                "Arquivos não encontrados:"
            )

            for file_name in missing:

                st.write(
                    f"• {file_name}"
                )