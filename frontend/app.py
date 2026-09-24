import logging
from datetime import datetime
import json
import os
from pathlib import Path
import re
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
from core.pipeline_validator import PipelineValidator

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
    page_title="MELLO BOT · Automation intelligence",
    page_icon=":material/auto_awesome:",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(circle at 78% -10%, #123c5c 0, #07131f 34rem); }
    [data-testid="stSidebar"] { background: #06101a; border-right: 1px solid #17344a; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #9ab4c8; }
    .mello-mark { display:flex; align-items:center; gap:.7rem; margin:.4rem 0 2.4rem; }
    .mello-mark-icon { width:2.25rem; height:2.25rem; display:grid; place-items:center; border-radius:.7rem; background:linear-gradient(135deg,#2f9bff,#49c5b6); color:#04111c; font-weight:800; }
    .mello-mark-title { color:#f2f8fc; font-weight:750; letter-spacing:.02em; font-size:1.1rem; }
    .mello-mark-subtitle { color:#6f8da5; font-size:.72rem; }
    .hero { padding: 3.6rem 0 2.2rem; max-width: 900px; }
    .eyebrow { color:#63b7ff; text-transform:uppercase; letter-spacing:.16em; font-size:.72rem; font-weight:700; }
    .hero h1 { font-size:clamp(2.8rem, 7vw, 5.7rem); line-height:.98; margin:.7rem 0 1rem; color:#f5fbff; letter-spacing:-.04em; }
    .hero p { color:#9ab4c8; font-size:1.15rem; max-width:650px; line-height:1.55; }
    .section-kicker { color:#6f8da5; text-transform:uppercase; letter-spacing:.12em; font-size:.72rem; font-weight:700; }
    .metric-card { padding:1.05rem 1.1rem; min-height:112px; border:1px solid #1c3b52; border-radius:12px; background:linear-gradient(145deg,#0d2435,#0a1a28); }
    .metric-label { color:#7f9bb0; font-size:.78rem; }
    .metric-value { color:#f5fbff; font-size:1.75rem; font-weight:700; margin-top:.35rem; }
    .metric-note { color:#55c4ae; font-size:.75rem; margin-top:.35rem; }
    .step-card { padding:1.1rem; min-height:150px; border:1px solid #1c3b52; border-radius:12px; background:#0a1a28; }
    .step-number { color:#2f9bff; font-size:.78rem; font-weight:800; }
    .step-title { color:#eff8ff; font-weight:700; margin:.7rem 0 .35rem; }
    .step-copy { color:#7894a8; font-size:.86rem; line-height:1.4; }
    .project-card { padding:1.2rem; border:1px solid #1c3b52; border-radius:12px; background:linear-gradient(145deg,#0d2435,#0a1a28); min-height:190px; }
    .project-title { color:#f2f8fc; font-size:1.05rem; font-weight:700; }
    .project-meta { color:#7894a8; font-size:.82rem; margin:.45rem 0 1rem; }
    .status-dot { color:#55c4ae; }
    @media (max-width: 700px) { .hero { padding-top:2rem; } .hero h1 { font-size:3rem; } }
    </style>
    """,
    unsafe_allow_html=True,
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


def call_ai_api(
    endpoint: str,
    prompt: str,
    payload: dict | None = None,
) -> dict:
    request = Request(
        f"{AI_API_URL.rstrip('/')}{endpoint}",
        data=json.dumps(payload or {"prompt": prompt}).encode("utf-8"),
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


def render_metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home_page(history: list[dict], projects: dict) -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">Automation intelligence platform</div>
            <h1>Transforme processos em automações.</h1>
            <p>Descreva um problema em linguagem natural. O MELLO AI estrutura a solução, cria o projeto e deixa sua equipe pronta para publicar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown("**Comece com uma ideia**")
        home_prompt = st.text_area(
            "Descreva o processo",
            placeholder="Recebo diariamente um relatório FS10N exportado do SAP e um relatório de Billing. Preciso identificar divergências.",
            height=120,
            key="home_prompt",
            label_visibility="collapsed",
        )
        action_col, example_col = st.columns([1, 1])
        with action_col:
            if st.button("🚀 Criar automação", type="primary", width="stretch"):
                if home_prompt.strip():
                    st.session_state["mello_ai_prompt"] = home_prompt
                    st.session_state["pending_navigation"] = "MELLO AI"
                    st.rerun()
                st.warning("Descreva o processo para começar.")
        with example_col:
            if st.button("📋 Ver exemplos", width="stretch"):
                st.session_state["pending_navigation"] = "MELLO AI"
                st.session_state["mello_ai_prompt"] = (
                    "Recebo diariamente um relatório FS10N exportado do SAP e um relatório de Billing. "
                    "Preciso conciliar os documentos e identificar divergências."
                )
                st.rerun()

    st.space("large")
    st.markdown('<div class="section-kicker">Visão executiva</div>', unsafe_allow_html=True)
    successful = sum(item.get("status") == "success" for item in history)
    success_rate = f"{round(successful / len(history) * 100)}%" if history else "—"
    metric_columns = st.columns(4)
    with metric_columns[0]:
        render_metric_card("Projetos criados", str(len(projects)), "Catálogo ativo")
    with metric_columns[1]:
        render_metric_card("Automações monitoradas", str(len(history)), "Histórico rastreável")
    with metric_columns[2]:
        render_metric_card("Taxa de sucesso", success_rate, "Execuções concluídas")
    with metric_columns[3]:
        render_metric_card("Outputs entregues", str(sum(len(item.get("outputs", [])) for item in history)), "Artefatos gerados")

    st.space("large")
    st.markdown('<div class="section-kicker">Como funciona</div>', unsafe_allow_html=True)
    steps = [
        ("01", "Descreva o processo", "Conte o que acontece hoje, com suas palavras."),
        ("02", "MELLO AI analisa", "Entradas, saídas, viabilidade e complexidade."),
        ("03", "Projeto gerado", "Manifesto, README e ETL base prontos para evoluir."),
        ("04", "Monitore a automação", "Execuções, outputs e histórico em um só lugar."),
    ]
    step_columns = st.columns(4)
    for column, (number, title, copy) in zip(step_columns, steps):
        with column:
            st.markdown(
                f'<div class="step-card"><div class="step-number">{number}</div><div class="step-title">{title}</div><div class="step-copy">{copy}</div></div>',
                unsafe_allow_html=True,
            )


def render_mello_ai_page() -> None:
    st.markdown('<div class="eyebrow">Copilot para automações</div>', unsafe_allow_html=True)
    st.title("MELLO AI", anchor=False)
    st.caption("Descreva um processo. Receba uma automação estruturada para revisar, publicar e monitorar.")

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
            width="stretch",
        )
    with manifest_col:
        manifest_clicked = st.button(
            "📄 Gerar Manifesto",
            disabled=not bool(st.session_state.get("mello_ai_analysis")),
            width="stretch",
        )
    with project_col:
        validation = st.session_state.get("mello_ai_pipeline_validation", {})
        project_clicked = st.button(
            "🚀 Aprovar e gerar projeto",
            disabled=(
                not bool(st.session_state.get("mello_ai_approved"))
                or not validation.get("valid", False)
            ),
            width="stretch",
        )

    if analyze_clicked:
        log_automation_event("ai_analysis_requested")
        try:
            st.session_state["mello_ai_analysis"] = call_ai_api(
                "/ai/analyze", prompt
            )
            st.session_state["mello_ai_manifest_data"] = st.session_state[
                "mello_ai_analysis"
            ].get("manifest_data", {})
            st.session_state["mello_ai_pipeline_validation"] = st.session_state[
                "mello_ai_analysis"
            ].get("pipeline_validation", {})
            st.session_state["mello_ai_reviewed_inputs"] = [
                dict(item)
                for item in st.session_state["mello_ai_manifest_data"].get(
                    "required_files", []
                )
            ]
            st.session_state["mello_ai_approved"] = False
            st.session_state.pop("mello_ai_project", None)
            st.session_state.pop("mello_ai_manifest", None)
            for key in list(st.session_state):
                if key.startswith("mello_ai_input_"):
                    st.session_state.pop(key)
            st.success("Processo analisado com sucesso.")
        except RuntimeError as error:
            st.error(str(error))

    if manifest_clicked:
        log_automation_event("ai_manifest_requested")
        try:
            response = call_ai_api(
                "/ai/manifest",
                prompt,
                payload={
                    "prompt": prompt,
                    "manifest_data": st.session_state.get(
                        "mello_ai_manifest_data"
                    ),
                },
            )
            st.session_state["mello_ai_manifest"] = response["manifest"]
            st.success("Manifesto gerado com sucesso.")
        except (RuntimeError, KeyError) as error:
            st.error(f"Não foi possível gerar o manifesto: {error}")

    if project_clicked:
        log_automation_event("ai_project_creation_requested")
        try:
            response = call_ai_api(
                "/ai/create-project",
                prompt,
                payload={
                    "prompt": prompt,
                    "manifest_data": st.session_state.get(
                        "mello_ai_manifest_data"
                    ),
                    "approved": bool(
                        st.session_state.get("mello_ai_approved")
                    ),
                },
            )
            st.session_state["mello_ai_project"] = response
            st.success("✅ Projeto criado com sucesso")
        except RuntimeError as error:
            st.error(f"Não foi possível criar o projeto: {error}")

    analysis = st.session_state.get("mello_ai_analysis")
    if analysis:
        st.divider()
        st.subheader("Revisão do rascunho")
        st.caption(
            "Confira os documentos, colunas críticas e outputs antes de aprovar a geração."
        )
        project_review_col, category_review_col = st.columns(2)
        project_review_col.write(
            f"**Projeto sugerido**\n\n`{analysis.get('project_id', '-')}`"
        )
        category_review_col.write(
            f"**Nome**\n\n{analysis.get('project_name', '-')} · "
            f"{analysis.get('category', '-')}"
        )
        understanding = analysis.get("understanding", {})
        st.info(
            f"Entendimento: {understanding.get('document_count', len(analysis.get('inputs', [])))} documentos · "
            f"{understanding.get('operation_count', len(analysis.get('steps', [])))} operações · "
            f"{understanding.get('output_count', len(analysis.get('outputs', [])))} outputs"
        )
        manifest_data = st.session_state.get("mello_ai_manifest_data", {})
        execution_plan = analysis.get("execution_plan", {})
        if execution_plan:
            st.subheader("Execution Plan")
            st.caption(execution_plan.get("summary", "Plano de execução sugerido."))
            intent_col, confidence_col, source_col = st.columns(3)
            intent_col.metric(
                "Intenção",
                execution_plan.get("intent", "Não identificada"),
            )
            confidence_col.metric(
                "Confiança",
                execution_plan.get("intent_confidence", "baixa").capitalize(),
            )
            source_col.metric(
                "Origem",
                ", ".join(execution_plan.get("intent_source", [])) or "nenhuma",
            )
            st.write(
                "**Resumo para aprovação**: "
                + execution_plan.get(
                    "intent_summary",
                    "O MELLO preparou um plano com base nas informações disponíveis.",
                )
            )
            plan_documents, plan_transformations = st.columns(2)
            with plan_documents:
                st.write("**Documentos identificados**")
                for document in execution_plan.get("documents", []):
                    st.write(
                        f"- `{document.get('id', '-')}`: "
                        f"{document.get('name', '-')} "
                        f"({document.get('source', '-')}, {document.get('format', '-')})"
                    )
            with plan_transformations:
                st.write("**Transformações**")
                decisions = execution_plan.get("decisions", [])
                transformations = decisions or execution_plan.get("transformations", [])
                quality_rules = [
                    transformation
                    for transformation in transformations
                    if transformation.get("operation") in {"remove_nulls", "drop_nulls", "validate"}
                ]
                for transformation in transformations:
                    if transformation in quality_rules:
                        continue
                    parameters = transformation.get(
                        "parameters",
                        transformation.get("details", {}),
                    )
                    suffix = f" — {parameters}" if parameters else ""
                    st.write(
                        f"{transformation.get('order', '')} "
                        f"{transformation.get('description', transformation.get('label', transformation.get('operation', '-')))}"
                        f"{suffix}"
                    )
                    st.caption(
                        f"Motivo: {transformation.get('reason', 'operação prevista no plano')} · "
                        f"Confiança: {transformation.get('confidence', 'baixa')} · "
                        f"Origem: {', '.join(transformation.get('source', [])) or 'nenhuma'}"
                    )
                    pending = transformation.get("pending_confirmation", [])
                    if pending:
                        st.warning("Pendente: " + ", ".join(pending))
                if quality_rules:
                    st.write("**Regras de qualidade**")
                    for rule in quality_rules:
                        parameters = rule.get("parameters", rule.get("details", {}))
                        if rule.get("operation") in {"remove_nulls", "drop_nulls"}:
                            st.write(
                                "- Remover registros com "
                                f"**{parameters.get('column', 'valor não informado')}** vazio"
                            )
                        else:
                            st.write("- Validar a qualidade dos dados")
            pending_questions = execution_plan.get("open_questions", [])
            if pending_questions:
                st.warning("**Pendências**\n\n" + "\n".join(f"- {item}" for item in pending_questions))
            risks = execution_plan.get("risks", [])
            if risks:
                st.error("**Riscos**\n\n" + "\n".join(f"- {item}" for item in risks))
            st.write("**Outputs**")
            workbook_sheets = manifest_data.get("workbook_sheets", [])
            if manifest_data.get("output_mode") == "workbook" and workbook_sheets:
                st.write(f"**Workbook:** `{manifest_data.get('workbook_name', 'resultado.xlsx')}`")
                st.write("**Abas**")
                for sheet in workbook_sheets:
                    st.write(f"- {sheet.rsplit('.', 1)[0].replace('_', ' ').title()}")
            else:
                output_details = execution_plan.get("output_details", [])
                if output_details:
                    for output in output_details:
                        st.write(f"- **{output.get('name', '-')}**: {output.get('reason', 'output previsto')}")
                else:
                    st.write(", ".join(execution_plan.get("outputs", [])) or "Nenhum output definido.")
        edited_project_name = st.text_input(
            "Nome do projeto",
            value=manifest_data.get("name", analysis.get("project_name", "")),
            key="mello_ai_project_name_editor",
        )
        manifest_data["name"] = edited_project_name
        diagnostic_col, viability_col, complexity_col = st.columns(3)
        diagnostic_col.info(analysis.get("diagnostic", "Sem diagnóstico."))
        viability_col.success(analysis.get("viability", "Viabilidade não informada."))
        complexity_col.warning(
            f"Complexidade: {analysis.get('complexity', 'não informada')}"
        )
        input_col, output_col = st.columns(2)
        with input_col:
            st.write("**Confirmar inputs**")
            st.caption(
                "Edite cada documento, remova sugestões incorretas ou adicione o que faltou."
            )
            reviewed_inputs = st.session_state.setdefault(
                "mello_ai_reviewed_inputs",
                [dict(item) for item in manifest_data.get("required_files", [])],
            )
            updated_inputs = []
            input_errors = []
            input_formats = ["xlsx", "csv", "xls", "json"]
            for index, input_file in enumerate(reviewed_inputs):
                input_key = re.sub(
                    r"[^a-z0-9]+",
                    "_",
                    str(input_file.get("id", f"input_{index}")).lower(),
                ).strip("_") or f"input_{index}"
                with st.container(border=True):
                    title_col, remove_col = st.columns([5, 1])
                    title_col.write(
                        f"**Documento {index + 1}:** "
                        f"{input_file.get('display_name', 'Sem nome')}"
                    )
                    remove_clicked = remove_col.button(
                        "Remover",
                        icon=":material/delete:",
                        key=f"mello_ai_input_remove_{input_key}",
                        width="stretch",
                    )
                    if remove_clicked:
                        reviewed_inputs.pop(index)
                        for key in list(st.session_state):
                            if key.startswith("mello_ai_input_"):
                                st.session_state.pop(key)
                        st.session_state["mello_ai_approved"] = False
                        st.rerun()
                    id_col, name_col, format_col = st.columns([2, 3, 2])
                    raw_id = id_col.text_input(
                        "ID",
                        value=input_file.get("id", ""),
                        key=f"mello_ai_input_id_{input_key}",
                    )
                    display_name = name_col.text_input(
                        "Nome",
                        value=input_file.get("display_name", ""),
                        key=f"mello_ai_input_name_{input_key}",
                    )
                    current_format = next(
                        iter(input_file.get("accepted_extensions", [])),
                        "xlsx",
                    )
                    format_index = (
                        input_formats.index(current_format)
                        if current_format in input_formats
                        else 0
                    )
                    extension = format_col.selectbox(
                        "Formato",
                        options=input_formats,
                        index=format_index,
                        key=f"mello_ai_input_format_{input_key}",
                    )
                    critical_columns = st.text_input(
                        "Colunas críticas",
                        value=", ".join(input_file.get("critical_columns", [])),
                        placeholder="Ex.: cnpj, valor",
                        key=f"mello_ai_input_columns_{input_key}",
                    )
                    input_id = re.sub(
                        r"[^a-z0-9]+", "_", raw_id.lower()
                    ).strip("_")
                    if not input_id or not display_name.strip():
                        input_errors.append("Cada input precisa de ID e nome.")
                        continue
                    updated_inputs.append(
                        {
                            "id": input_id,
                            "display_name": display_name.strip(),
                            "cli_argument": f"--{input_id.replace('_', '-')}",
                            "accepted_extensions": [extension],
                            "critical_columns": [
                                column.strip()
                                for column in critical_columns.split(",")
                                if column.strip()
                            ],
                            "required_columns": input_file.get(
                                "required_columns", []
                            ),
                        }
                    )
            st.write("**Adicionar documento**")
            with st.form("mello_ai_add_input", border=False, clear_on_submit=True):
                new_id_col, new_name_col, new_format_col = st.columns([2, 3, 2])
                new_id = new_id_col.text_input(
                    "ID do documento",
                    placeholder="metas_comerciais",
                )
                new_name = new_name_col.text_input(
                    "Nome do documento",
                    placeholder="Metas Comerciais",
                )
                new_extension = new_format_col.selectbox(
                    "Formato do documento",
                    options=input_formats,
                )
                new_critical_columns = st.text_input(
                    "Colunas críticas do documento",
                    placeholder="Ex.: regiao, meta",
                )
                add_document = st.form_submit_button(
                    "Adicionar documento",
                    icon=":material/add:",
                    width="stretch",
                )
            if add_document:
                new_input_id = re.sub(
                    r"[^a-z0-9]+", "_", new_id.lower()
                ).strip("_")
                existing_ids = {item["id"] for item in updated_inputs}
                if not new_input_id or not new_name.strip():
                    st.error("Informe o ID e o nome do documento para adicioná-lo.")
                elif new_input_id in existing_ids:
                    st.error("Já existe um documento com esse ID.")
                else:
                    reviewed_inputs.append(
                        {
                            "id": new_input_id,
                            "display_name": new_name.strip(),
                            "cli_argument": f"--{new_input_id.replace('_', '-')}",
                            "accepted_extensions": [new_extension],
                            "critical_columns": [
                                column.strip()
                                for column in new_critical_columns.split(",")
                                if column.strip()
                            ],
                            "required_columns": [],
                        }
                    )
                    st.session_state["mello_ai_approved"] = False
                    st.rerun()
            if updated_inputs != reviewed_inputs:
                st.session_state["mello_ai_approved"] = False
                st.session_state["mello_ai_reviewed_inputs"] = updated_inputs
            if not updated_inputs:
                input_errors.append("Confirme pelo menos um input para criar o projeto.")
            if len({item["id"] for item in updated_inputs}) != len(updated_inputs):
                input_errors.append("Os IDs dos inputs precisam ser únicos.")
            manifest_data["required_files"] = updated_inputs
        with output_col:
            st.write("**Outputs editáveis**")
            output_mode = st.radio(
                "Formato de entrega",
                options=["separate", "workbook"],
                format_func=lambda value: (
                    "Outputs separados"
                    if value == "separate"
                    else "Workbook único com abas"
                ),
                index=(
                    1
                    if manifest_data.get("output_mode") == "workbook"
                    else 0
                ),
                key="mello_ai_output_mode",
                horizontal=True,
            )
            manifest_data["output_mode"] = output_mode
            edited_outputs = st.data_editor(
                [{"output": output} for output in manifest_data.get(
                    "outputs", analysis.get("outputs", [])
                )],
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                key="mello_ai_outputs_editor",
            )
            output_rows = (
                edited_outputs.to_dict(orient="records")
                if hasattr(edited_outputs, "to_dict")
                else edited_outputs
            )
            selected_outputs = [
                row["output"]
                for row in output_rows
                if row.get("output")
            ]
            if output_mode == "workbook":
                manifest_data["workbook_sheets"] = selected_outputs
            manifest_data["outputs"] = selected_outputs
            if output_mode == "workbook":
                workbook_name = st.text_input(
                    "Nome do workbook",
                    value=manifest_data.get(
                        "workbook_name",
                        "relatorio_analitico.xlsx",
                    ),
                    key="mello_ai_workbook_name",
                )
                manifest_data["workbook_name"] = workbook_name
                manifest_data["outputs"] = [workbook_name]
        pipeline_validation = PipelineValidator.validate(manifest_data)
        if input_errors:
            pipeline_validation = {
                **pipeline_validation,
                "valid": False,
                "errors": pipeline_validation["errors"] + input_errors,
            }
        st.session_state["mello_ai_pipeline_validation"] = pipeline_validation
        st.write("**Validação do pipeline**")
        if pipeline_validation["valid"]:
            st.success(
                f"Pipeline consistente: {pipeline_validation['input_count']} documentos, "
                f"{pipeline_validation['step_count']} operações e "
                f"{pipeline_validation['output_count']} outputs."
            )
        else:
            for error in pipeline_validation["errors"]:
                st.error(error)
        st.write("**Pipeline draft**")
        edited_steps = st.data_editor(
            manifest_data.get("steps", analysis.get("steps", [])),
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key="mello_ai_steps_editor",
        )
        manifest_data["steps"] = (
            edited_steps.to_dict(orient="records")
            if hasattr(edited_steps, "to_dict")
            else edited_steps
        )
        pipeline_validation = PipelineValidator.validate(manifest_data)
        if input_errors:
            pipeline_validation = {
                **pipeline_validation,
                "valid": False,
                "errors": pipeline_validation["errors"] + input_errors,
            }
        st.session_state["mello_ai_pipeline_validation"] = pipeline_validation
        st.session_state["mello_ai_manifest_data"] = manifest_data
        st.divider()
        approved = st.checkbox(
            "Aprovo este rascunho para gerar o projeto",
            disabled=not pipeline_validation["valid"],
            key="mello_ai_approved",
        )
        if approved:
            st.success("Rascunho aprovado. A geração do projeto está liberada.")

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
    st.markdown('<div class="eyebrow">Governança</div>', unsafe_allow_html=True)
    st.title("Projetos", anchor=False)
    st.caption("O catálogo central das automações da sua organização.")

    project_columns = st.columns(2)
    for index, project in enumerate(projects.values()):
        with project_columns[index % 2]:
            st.markdown(
                f"""
                <div class="project-card">
                    <div class="project-title">{project.name}</div>
                    <div class="project-meta"><span class="status-dot">●</span> Ativo &nbsp; · &nbsp; {project.category.title()}</div>
                    <div class="project-meta">{project.description}</div>
                    <div class="project-meta">{len(project.required_files)} inputs &nbsp; · &nbsp; {len(project.outputs)} outputs</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            action_col, manifest_col = st.columns(2)
            with action_col:
                if st.button("Executar", key=f"project_run_{project.id}", width="stretch"):
                    st.session_state["pending_navigation"] = "Execuções"
                    st.rerun()
            with manifest_col:
                if st.button("Manifesto", key=f"project_manifest_{project.id}", width="stretch"):
                    st.session_state["pending_navigation"] = "Administração"
                    st.rerun()


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

pending_navigation = st.session_state.pop("pending_navigation", None)
if pending_navigation is not None:
    st.session_state["navigation"] = pending_navigation

with st.sidebar:

    st.markdown(
        """
        <div class="mello-mark">
            <div class="mello-mark-icon">M</div>
            <div><div class="mello-mark-title">MELLO BOT</div><div class="mello-mark-subtitle">Automation intelligence</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    navigation = st.radio(
        "Workspace",
        [
            "Visão geral",
            "MELLO AI",
            "Projetos",
            "Execuções",
            "Histórico",
            "Outputs",
            "Administração",
            "Diagnóstico",
        ],
        key="navigation",
    )
    st.markdown("---")
    st.caption("MELLO BOT · V1")

history = load_history()

# =============================================================================
# MAIN
# =============================================================================

projects = {
    project.id: project
    for project in Orchestrator.list_projects()
}

if navigation == "MELLO AI":
    render_mello_ai_page()
    st.stop()

if navigation == "Visão geral":
    render_home_page(history, projects)
    st.stop()

if navigation == "Histórico":
    render_history_page(history)
    st.stop()

if navigation == "Projetos":
    render_projects_page(projects)
    st.stop()

if navigation == "Outputs":
    render_outputs_page(projects)
    st.stop()

if navigation == "Administração":
    render_admin_page()
    st.stop()

if navigation == "Diagnóstico":
    render_health_page()
    st.stop()

# Execuções mantém o fluxo operacional existente abaixo.

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