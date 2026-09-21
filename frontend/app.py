import logging
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st
import streamlit.components.v1 as components



# =============================================================================
# IMPORTS
# =============================================================================

from core.history_service import HistoryService
from core.logger import log_automation_event
from core.orchestrator import Orchestrator

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
    project: object,
    uploaded_files: dict,
) -> tuple[list[dict], bool]:
    return Orchestrator.validate_uploaded_files(
        project_id=project_id,
        project=project,
        uploaded_files=uploaded_files,
    )


def load_history() -> list[dict]:
    try:
        return HistoryService.get_history(limit=100)
    except Exception:
        logger.exception("Erro carregando histórico")
        return []


AI_API_URL = os.getenv("MELLO_BOT_API_URL", "http://localhost:8000")


def call_ai_api(endpoint: str, prompt: str) -> dict:
    request = Request(
        f"{AI_API_URL.rstrip('/')}{endpoint}",
        data=json.dumps({"prompt": prompt}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            payload = json.loads(error.read().decode("utf-8"))
            detail = payload.get("detail", "A API recusou a solicitação.")
        except (ValueError, UnicodeDecodeError):
            detail = "A API recusou a solicitação."
        raise RuntimeError(f"{detail} (HTTP {error.code})") from error
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError(
            "Não foi possível conectar à API. Inicie scripts\\start_mello_bot_api.bat."
        ) from error


def read_artifact(path_value: str, fallback: str = "") -> str:
    try:
        return Path(path_value).read_text(encoding="utf-8")
    except (OSError, TypeError):
        return fallback


def render_copy_button(content: str) -> None:
    encoded_content = json.dumps(content)
    components.html(
        f"""
        <button id="copy-manifest" style="padding: .45rem .8rem; cursor: pointer;">
            📋 Copiar Manifesto
        </button>
        <span id="copy-status" style="margin-left: .5rem;"></span>
        <script>
        const content = {encoded_content};
        const button = document.getElementById("copy-manifest");
        const status = document.getElementById("copy-status");
        button.addEventListener("click", async () => {{
            try {{
                await navigator.clipboard.writeText(content);
                status.textContent = "Copiado";
            }} catch (error) {{
                status.textContent = "Selecione e copie o conteúdo acima";
            }}
        }});
        </script>
        """,
        height=42,
    )


def render_mello_ai_page() -> None:
    st.header("🤖 MELLO AI")
    st.caption(
        "Descreva um processo em linguagem natural e o MELLO BOT irá analisar, "
        "gerar o manifesto e criar a estrutura inicial da automação."
    )

    examples = {
        "SAP x Billing": (
            "Recebo diariamente um relatório FS10N exportado do SAP e um relatório "
            "de Billing. Preciso conciliar os documentos e gerar um Excel contendo "
            "conciliados, divergentes, apenas SAP e apenas Billing."
        ),
        "SAP x Prefeitura": (
            "Recebo relatórios do SAP e da Prefeitura. Preciso conciliar notas "
            "fiscais e gerar um relatório de divergências."
        ),
        "Antifraude": (
            "Recebo uma base de transações e preciso classificar registros "
            "suspeitos para análise antifraude."
        ),
        "Power BI Dataset": (
            "Recebo uma base operacional e preciso preparar um dataset para "
            "consumo no Power BI."
        ),
    }
    st.write("**Exemplos rápidos**")
    example_columns = st.columns(len(examples))
    for column, (label, example) in zip(example_columns, examples.items()):
        if column.button(label, use_container_width=True, key=f"ai_example_{label}"):
            st.session_state["mello_ai_prompt"] = example

    prompt = st.text_area(
        "Descreva o processo",
        key="mello_ai_prompt",
        height=180,
        placeholder=(
            "Recebo diariamente um relatório FS10N exportado do SAP e um relatório "
            "de Billing.\n\nPreciso conciliar os documentos e gerar um Excel "
            "contendo conciliados, divergentes, apenas SAP e apenas Billing."
        ),
    )
    if not prompt.strip():
        st.info("Descreva o processo ou escolha um exemplo rápido para começar.")
        return

    analysis_col, manifest_col, project_col = st.columns(3)
    with analysis_col:
        analyze_clicked = st.button(
            "🔍 Analisar Processo",
            type="primary",
            use_container_width=True,
        )
    with manifest_col:
        manifest_clicked = st.button(
            "📄 Gerar Manifesto",
            use_container_width=True,
        )
    with project_col:
        project_clicked = st.button(
            "🚀 Criar Projeto",
            use_container_width=True,
        )

    if analyze_clicked:
        log_automation_event("ai_analysis_requested")
        try:
            st.session_state["mello_ai_analysis"] = call_ai_api(
                "/ai/analyze", prompt
            )
            st.success("Processo analisado com sucesso.")
        except RuntimeError as error:
            st.error(str(error))

    if manifest_clicked:
        log_automation_event("ai_manifest_requested")
        try:
            response = call_ai_api("/ai/manifest", prompt)
            st.session_state["mello_ai_manifest"] = response["manifest"]
            st.success("Manifesto gerado com sucesso.")
        except (RuntimeError, KeyError) as error:
            st.error(f"Não foi possível gerar o manifesto: {error}")

    if project_clicked:
        log_automation_event("ai_project_creation_requested")
        try:
            response = call_ai_api("/ai/create-project", prompt)
            st.session_state["mello_ai_project"] = response
            st.success("✅ Projeto criado com sucesso")
        except RuntimeError as error:
            st.error(f"Não foi possível criar o projeto: {error}")

    analysis = st.session_state.get("mello_ai_analysis")
    if analysis:
        st.divider()
        st.subheader("Análise do processo")
        diagnostic_col, viability_col, complexity_col = st.columns(3)
        diagnostic_col.info(analysis.get("diagnostic", "Sem diagnóstico."))
        viability_col.success(analysis.get("viability", "Viabilidade não informada."))
        complexity_col.warning(
            f"Complexidade: {analysis.get('complexity', 'não informada')}"
        )
        input_col, output_col = st.columns(2)
        with input_col:
            st.write("**Inputs identificados**")
            for item in analysis.get("inputs", []):
                st.write(
                    f"- `{item.get('id', '-')}`: {item.get('display_name', '-') } "
                    f"({', '.join(item.get('accepted_extensions', [item.get('extension', '-')]))})"
                )
        with output_col:
            st.write("**Outputs esperados**")
            for output in analysis.get("outputs", []):
                st.write(f"- `{output}`")

    manifest = st.session_state.get("mello_ai_manifest")
    if manifest:
        st.divider()
        st.subheader("Manifesto gerado")
        st.code(manifest, language="yaml")
        render_copy_button(manifest)

    project = st.session_state.get("mello_ai_project")
    if project:
        st.divider()
        st.subheader("Artefatos do projeto")
        st.success("✅ Projeto criado com sucesso")
        details = st.columns(3)
        details[0].write(f"**Project ID**\n\n`{project.get('project_id', '-')}`")
        details[1].write(f"**Project Path**\n\n`{project.get('project_path', '-')}`")
        details[2].write(f"**Status**\n\n`{project.get('status', '-')}`")

        manifest_content = read_artifact(
            project.get("manifest_path"),
            manifest or "Manifesto não disponível.",
        )
        readme_content = read_artifact(
            project.get("readme_path"),
            "README não disponível.",
        )
        main_content = read_artifact(
            project.get("entrypoint_path"),
            "Entrypoint não disponível.",
        )
        manifest_tab, readme_tab, main_tab = st.tabs(
            ["manifest.yaml", "README.md", "main.py"]
        )
        with manifest_tab:
            st.code(manifest_content, language="yaml")
        with readme_tab:
            st.code(readme_content, language="markdown")
        with main_tab:
            st.code(main_content, language="python")


def render_dashboard(history: list[dict], project_count: int) -> None:
    successful_runs = sum(
        execution.get("status") == "success"
        for execution in history
    )
    success_rate = (
        round(successful_runs / len(history) * 100)
        if history
        else 0
    )
    failures = sum(
        execution.get("status") in {"failed", "error"}
        for execution in history
    )
    generated_outputs = sum(
        len(execution.get("outputs", []))
        for execution in history
    )
    latest_duration = (
        history[0].get(
            "duration_seconds",
            "-",
        )
        if history
        else "-"
    )

    col_projects, col_runs, col_success = st.columns(3)
    col_failures, col_outputs, col_duration = st.columns(3)
    col_projects.metric("Projetos", project_count)
    col_runs.metric("Execuções", len(history))
    col_success.metric("Sucesso", f"{success_rate}%")
    col_failures.metric("Falhas", failures)
    col_outputs.metric("Outputs gerados", generated_outputs)
    col_duration.metric("Última execução", f"{latest_duration}s")


def format_execution_status(status: str) -> str:
    return {
        "success": "✅ Sucesso",
        "partial_success": "⚠ Parcial",
        "partial": "⚠ Parcial",
        "failed": "❌ Falha",
        "error": "❌ Falha",
    }.get(status, f"⚠ {status}")


def format_execution_date(execution: dict) -> str:
    raw_date = execution.get(
        "finished_at",
        execution.get("end_time", ""),
    )

    if not raw_date:
        return "-"

    try:
        return datetime.fromisoformat(raw_date).strftime(
            "%d/%m/%Y %H:%M"
        )
    except (TypeError, ValueError):
        return str(raw_date)


def render_history_page(history: list[dict]) -> None:
    st.header("Histórico de execuções")

    if not history:
        st.info("Nenhuma execução encontrada.")
        return

    rows = []
    for execution in history:
        status = execution.get("status", "-")
        rows.append(
            {
                "Projeto": execution.get("project_id", "-"),
                "Status": format_execution_status(status),
                "Tempo (s)": execution.get("duration_seconds", "-"),
                "Data": format_execution_date(execution),
                "Execução": execution.get("execution_id", "-"),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)

    selected_index = st.selectbox(
        "Ver detalhes da execução",
        options=range(len(history)),
        format_func=lambda index: (
            f"{history[index].get('project_id', '-')} · "
            f"{format_execution_date(history[index])} · "
            f"{format_execution_status(history[index].get('status', '-'))}"
        ),
    )
    selected_execution = history[selected_index]

    st.subheader("Detalhes da execução")
    detail_project, detail_status, detail_duration = st.columns(3)
    detail_project.metric(
        "Projeto",
        selected_execution.get("project_id", "-"),
    )
    detail_status.metric(
        "Status",
        format_execution_status(selected_execution.get("status", "-")),
    )
    detail_duration.metric(
        "Duração",
        f"{selected_execution.get('duration_seconds', '-')}s",
    )
    st.write(
        f"**Execution ID:** `{selected_execution.get('execution_id', '-')}`"
    )

    outputs = selected_execution.get("outputs", [])
    st.write("**Outputs:**")
    if outputs:
        for output in outputs:
            st.write(f"- {output}")
    else:
        st.caption("Nenhum output registrado.")


def render_projects_page(projects: dict) -> None:
    st.header("Projetos")

    project_columns = st.columns(2)
    for index, project in enumerate(projects.values()):
        with project_columns[index % 2]:
            with st.container(border=True):
                st.subheader(f"📦 {project.name}")
                st.caption(project.category.title())
                st.write(project.description)
                st.write(
                    f"**{len(project.required_files)}** arquivo(s) de entrada"
                )
                st.write(f"**{len(project.outputs)}** output(s)")
                st.caption("Outputs: " + ", ".join(project.outputs))


def render_outputs_page(projects: dict) -> None:
    st.header("Outputs")

    output_rows = []
    for project in projects.values():
        output_folder = Orchestrator.get_project_output_folder(project)
        for output_name in project.outputs:
            output_path = output_folder / output_name
            if output_path.exists():
                output_rows.append((project, output_name, output_path))

    if not output_rows:
        st.info("Nenhum output gerado ainda.")
        return

    for project, output_name, output_path in output_rows:
        with st.container(border=True):
            details, action = st.columns([4, 1])
            details.write(f"**{output_name}**")
            details.caption(
                f"{project.name} · "
                f"{output_path.stat().st_size / 1024:.1f} KB · "
                f"{datetime.fromtimestamp(output_path.stat().st_mtime):%d/%m/%Y %H:%M}"
            )
            action.download_button(
                "Download",
                data=output_path.read_bytes(),
                file_name=output_name,
                key=f"output_{project.id}_{output_name}",
            )


def render_admin_page() -> None:
    st.header("Administração")
    st.caption("Manifestos existentes e estrutura dos projetos.")

    manifest_files = Orchestrator.list_manifest_files()
    if not manifest_files:
        st.info("Nenhum manifesto encontrado.")
        return

    for manifest_path in manifest_files:
        with st.expander(manifest_path.stem):
            manifest_yaml = Orchestrator.read_manifest_yaml(manifest_path)

            try:
                manifest = Orchestrator.validate_manifest_yaml(manifest_yaml)
                st.success("Manifesto válido")
                card_col, action_col = st.columns([3, 1])
                card_col.write(f"**Projeto:** {manifest.name}")
                card_col.write(
                    f"**Arquivos:** {len(manifest.required_files)} · "
                    f"**Outputs:** {len(manifest.outputs)}"
                )
                card_col.write(
                    f"**Última alteração:** "
                    f"{datetime.fromtimestamp(manifest_path.stat().st_mtime):%d/%m/%Y}"
                )
                action_col.download_button(
                    "Download YAML",
                    data=manifest_yaml,
                    file_name=manifest_path.name,
                    key=f"manifest_download_{manifest_path.stem}",
                )
                if st.button(
                    "Validar YAML",
                    key=f"manifest_validate_{manifest_path.stem}",
                    use_container_width=True,
                ):
                    st.success("Manifesto válido")
                edited_yaml = st.text_area(
                    "YAML",
                    value=manifest_yaml,
                    height=220,
                    key=f"manifest_copy_{manifest_path.stem}",
                )
                if st.button(
                    "Salvar edição como nova versão",
                    key=f"manifest_edit_{manifest_path.stem}",
                    use_container_width=True,
                ):
                    try:
                        edited_manifest = Orchestrator.validate_manifest_yaml(
                            edited_yaml
                        )
                        saved_path = Orchestrator.save_versioned_manifest(
                            edited_manifest
                        )
                        st.success(f"Manifesto atualizado em {saved_path}")
                    except Exception as error:
                        st.error(f"Não foi possível salvar: {error}")
                confirm_delete = st.checkbox(
                    "Confirmo a exclusão deste projeto",
                    key=f"manifest_delete_confirm_{manifest_path.stem}",
                )
                if st.button(
                    "Apagar projeto",
                    key=f"manifest_delete_{manifest_path.stem}",
                    disabled=not confirm_delete,
                    use_container_width=True,
                ):
                    try:
                        deleted_path = Orchestrator.delete_project(manifest.id)
                        st.success(f"Projeto apagado: {deleted_path}")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Não foi possível apagar: {error}")
                versions = Orchestrator.list_manifest_versions(manifest.id)
                if versions:
                    st.write("**Versões anteriores**")
                    for version in versions:
                        st.caption(version.name)
            except Exception as error:
                st.error(f"Manifesto inválido: {error}")


def render_health_page() -> None:
    st.header("Diagnóstico")
    diagnosis = Orchestrator.diagnose()
    metrics = st.columns(5)
    metrics[0].metric("Manifestos válidos", diagnosis["valid_manifests"])
    metrics[1].metric("Projetos encontrados", diagnosis["projects_found"])
    metrics[2].metric("Caminhos válidos", diagnosis["valid_paths"])
    metrics[3].metric("Entrypoints encontrados", diagnosis["entrypoints_found"])
    metrics[4].metric("Outputs acessíveis", diagnosis["accessible_outputs"])

    for item in diagnosis["details"]:
        if item["error"]:
            st.error(f"✗ {item['id']}: {item['error']}")
        else:
            st.write(
                f"{'✓' if item['valid'] else '✗'} **{item['id']}** · "
                f"caminho {'✓' if item['project_path'] else '✗'} · "
                f"entrypoint {'✓' if item['entrypoint'] else '✗'} · "
                f"outputs {'✓' if item['outputs'] else '✗'}"
            )


def render_create_project_page() -> None:
    st.header("Criar Projeto")
    st.caption("Gere um manifesto a partir de um arquivo de exemplo.")

    sample_file = st.file_uploader(
        "1. Upload arquivo exemplo",
        type=["csv", "xlsx", "xls"],
        key="manifest_sample_file",
    )

    if sample_file is None:
        st.info("Envie um CSV ou XLSX para começar.")
        return

    try:
        suffix = Path(sample_file.name).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
            temporary_file.write(sample_file.getbuffer())
            temporary_path = Path(temporary_file.name)

        columns = Orchestrator.extract_columns(temporary_path)
    except Exception as error:
        st.error(f"Não foi possível extrair as colunas: {error}")
        return
    finally:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)

    st.success(f"2. {len(columns)} coluna(s) extraída(s)")
    suggestions = Orchestrator.suggest_manifest(sample_file.name, columns)
    st.info(
        "Copilot determinístico: sugestões geradas a partir do nome do arquivo "
        "e das colunas. Revise antes de salvar."
    )
    analysis_col, columns_col = st.columns([1, 2])
    analysis_col.metric("Linhas de cabeçalho", len(columns))
    analysis_col.caption(f"Formato detectado: {suffix.lstrip('.').upper()}")
    columns_col.write("**3. Estrutura identificada**")
    columns_col.write("\n".join(f"- {column}" for column in columns))

    form_col, preview_col = st.columns([1, 1])
    with form_col:
        project_id = st.text_input(
            "ID do projeto",
            value=suggestions["project_id"],
        )
        project_name = st.text_input(
            "Nome do projeto",
            value=suggestions["name"],
        )
        category = st.text_input(
            "Categoria",
            value=suggestions["category"],
        )
        description = st.text_area(
            "Descrição",
            value=suggestions["description"],
        )
        project_path = st.text_input(
            "Caminho do projeto",
            value=f"projects/{Path(sample_file.name).stem.lower().replace(' ', '_')}",
        )
        entrypoint = st.text_input("Script de entrada", value="src/main.py")
        file_id = st.text_input(
            "ID do arquivo de entrada",
            value=Path(sample_file.name).stem.lower().replace(" ", "_"),
        )
        display_name = st.text_input(
            "Nome exibido do arquivo",
            value=suggestions["display_name"],
        )
        required_columns = st.multiselect(
            "4. Quais colunas fazem parte do processo?",
            options=columns,
            default=columns,
        )
        outputs = [
            output.strip()
            for output in st.text_input(
                "5. Quais outputs pretende gerar? (separados por vírgula)",
                value="resultado.xlsx",
            ).split(",")
            if output.strip()
        ]

    with preview_col:
        if not project_id or not project_name or not required_columns or not outputs:
            st.warning("Preencha ID, nome, colunas e outputs para gerar o manifesto.")
            return

        try:
            manifest_data = Orchestrator.build_manifest_data(
                project_id=project_id,
                name=project_name,
                category=category,
                description=description,
                project_path=project_path,
                entrypoint=entrypoint,
                file_id=file_id,
                display_name=display_name,
                extension=suffix.lstrip("."),
                required_columns=required_columns,
                outputs=outputs,
            )
            manifest = Orchestrator.validate_manifest(manifest_data)
        except Exception as error:
            st.error(f"Manifesto inválido: {error}")
            return

        st.success("6. Manifesto validado")
        st.code(Orchestrator.manifest_to_yaml(manifest), language="yaml")

        if st.button(
            "7. Salvar e gerar estrutura",
            type="primary",
            use_container_width=True,
        ):
            try:
                manifest_path, project_path = Orchestrator.create_project(manifest)
                st.success(
                    f"Manifesto salvo em {manifest_path}. "
                    f"Estrutura criada em {project_path}."
                )
            except FileExistsError as error:
                st.warning(str(error))
            except Exception as error:
                st.error(f"Erro ao salvar manifesto: {error}")


# =============================================================================
# FILE MANAGER INIT
# =============================================================================

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:

    st.header("MELLO BOT")
    navigation = st.radio(
        "Navegação",
        [
            "🤖 MELLO AI",
            "Executar",
            "Histórico",
            "Projetos",
            "Outputs",
            "Criar Projeto",
            "Administração",
            "Diagnóstico",
        ],
    )

history = load_history()

# =============================================================================
# MAIN
# =============================================================================

st.title("🤖 MELLO BOT")

projects = {
    project.id: project
    for project in Orchestrator.list_projects()
}

render_dashboard(history, len(projects))

if navigation == "Histórico":
    render_history_page(history)
    st.stop()

if navigation == "🤖 MELLO AI":
    render_mello_ai_page()
    st.stop()

if navigation == "Projetos":
    render_projects_page(projects)
    st.stop()

if navigation == "Outputs":
    render_outputs_page(projects)
    st.stop()

if navigation == "Criar Projeto":
    render_create_project_page()
    st.stop()

if navigation == "Administração":
    render_admin_page()
    st.stop()

if navigation == "Diagnóstico":
    render_health_page()
    st.stop()

selected_project_id = st.selectbox(
    "Selecione um ETL",
    options=list(projects.keys()),
    format_func=lambda x: projects[x].name,
)

project = projects[selected_project_id]

st.subheader(project.name)
st.write(project.description)

st.divider()

# =============================================================================
# UPLOADS
# =============================================================================

st.subheader(
    "Arquivos obrigatórios"
)

uploaded_files = {}

for file_definition in project.required_files:

    uploaded_files[
        file_definition.id
    ] = st.file_uploader(
        label=file_definition.display_name,
        type=file_definition.accepted_extensions,
        key=file_definition.id,
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

    validation_results, all_files_valid = validate_uploaded_files(
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
                f"{result['display_name']} - Score: {result['score']}%"
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
    use_container_width=True,
):

    try:

        with st.spinner(
            "Executando ETL..."
        ):

            run_result = Orchestrator.run_project(
                project_id=selected_project_id,
                uploaded_files=list(uploaded_files.values()),
            )

        output_result = Orchestrator.validate_outputs(project)

        st.session_state[
            "output_result"
        ] = output_result

        st.session_state[
            "output_project_id"
        ] = selected_project_id

        found = output_result.get(
            "found",
            [],
        )

        missing = output_result.get(
            "missing",
            [],
        )

        st.success(
            "ETL executado com sucesso!"
        )

    except Exception as error:

        logger.exception(
            "Erro executando ETL"
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