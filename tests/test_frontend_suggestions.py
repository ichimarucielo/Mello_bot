from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from core.ai_service import MockAIService


def test_grouping_suggestion_is_applied_only_after_user_confirmation():
    prompt = (
        "Recebo dois relatórios ZSD008, um antigo e um novo. "
        "Quero comparar."
    )
    payload = MockAIService().analyze(prompt).model_dump(mode="json")
    app = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "frontend" / "app.py",
        default_timeout=30,
    )
    for key, value in {
        "navigation": "MELLO AI",
        "mello_ai_prompt": prompt,
        "mello_ai_analysis": payload,
        "mello_ai_manifest_data": payload["manifest_data"],
        "mello_ai_pipeline_validation": payload["pipeline_validation"],
    }.items():
        app.session_state[key] = value

    with patch(
        "core.history_service.HistoryService.get_history",
        return_value=[],
    ), patch("core.orchestrator.Orchestrator.list_projects", return_value=[]):
        app.run()

        manifest = app.session_state["mello_ai_manifest_data"]
        assert not any(step.get("type") == "aggregate" for step in manifest["steps"])

        button = next(
            item
            for item in app.button
            if "Confirmar e adicionar agrupamento" in item.label
        )
        button.click().run()

    assert not app.exception, [str(error) for error in app.exception]
    manifest = app.session_state["mello_ai_manifest_data"]
    assert sum(step.get("type") == "aggregate" for step in manifest["steps"]) == 1
    assert sum(
        step.get("operation") == "aggregate"
        for step in manifest["pipeline"]["operations"]
    ) == 1
    assert app.session_state["mello_ai_pipeline_validation"]["valid"]
    plan = app.session_state["mello_ai_analysis"]["execution_plan"]
    assert plan["suggestions"] == []
    assert plan["decisions"][-1]["source"] == ["confirmacao_humana"]


def test_workbook_sheet_editor_renders_requested_tab_names():
    prompt = (
        "Recebo FS10N e Billing em um único workbook com as abas: "
        "Resumo Executivo, Conciliados, Divergências, Apenas FS10N e Apenas Billing."
    )
    payload = MockAIService().analyze(prompt).model_dump(mode="json")
    app = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "frontend" / "app.py",
        default_timeout=30,
    )
    for key, value in {
        "navigation": "MELLO AI",
        "mello_ai_prompt": prompt,
        "mello_ai_analysis": payload,
        "mello_ai_manifest_data": payload["manifest_data"],
        "mello_ai_pipeline_validation": payload["pipeline_validation"],
    }.items():
        app.session_state[key] = value

    with patch(
        "core.history_service.HistoryService.get_history",
        return_value=[],
    ), patch("core.orchestrator.Orchestrator.list_projects", return_value=[]):
        app.run()

    assert not app.exception, [str(error) for error in app.exception]
    sheet_editor_data = next(
        frame.value
        for frame in app.dataframe
        if list(frame.value.columns) == ["aba"]
    )
    assert sheet_editor_data["aba"].tolist() == [
        "Resumo Executivo",
        "Conciliados",
        "Divergências",
        "Apenas FS10N",
        "Apenas Billing",
    ]