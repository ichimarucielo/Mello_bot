from pathlib import Path

from core.ai_service import AIService, MockAIService
from core.logger import log_automation_event
from core.manifest_generator import ManifestGenerator
from core.models import (
    AutomationAnalysis,
    AutomationGenerationResult,
)
from core.project_scaffolder import ProjectScaffolder
from core.settings import MANIFESTS_DIR


class AutomationDesigner:
    """Coordena analise, manifesto e criacao de um scaffold de automacao."""

    def __init__(self, ai_service: AIService | None = None):
        self.ai_service = ai_service or MockAIService()

    def analyze(self, prompt: str) -> AutomationAnalysis:
        log_automation_event("automation_requested", prompt=prompt)
        analysis = self.ai_service.analyze(prompt)
        log_automation_event(
            "automation_analyzed",
            project_id=analysis.project_id,
            complexity=analysis.complexity,
            viability=analysis.viability,
        )
        return analysis

    def generate_manifest(self, prompt: str) -> str:
        analysis = self.analyze(prompt)
        manifest = ManifestGenerator.validate(analysis.manifest_data)
        manifest_yaml = ManifestGenerator.to_yaml(manifest)
        log_automation_event(
            "manifest_generated",
            project_id=manifest.id,
            outputs=manifest.outputs,
        )
        return manifest_yaml

    def create_project(self, prompt: str) -> AutomationGenerationResult:
        analysis = self.analyze(prompt)
        return self.create_project_from_manifest(
            analysis.manifest_data,
            pattern=analysis.pattern,
            analysis=analysis,
        )

    def create_project_from_manifest(
        self,
        manifest_data: dict,
        pattern: str = "generic",
        analysis: AutomationAnalysis | None = None,
    ) -> AutomationGenerationResult:
        manifest = ManifestGenerator.validate(manifest_data)
        analysis = analysis or self._analysis_from_manifest(manifest)
        artifacts = ProjectScaffolder.create_automation_project(
            manifest,
            pattern=pattern,
        )
        published_manifest = self._publish_manifest(
            source_manifest=Path(artifacts["manifest_path"]),
            project_id=manifest.id,
        )
        log_automation_event(
            "manifest_generated",
            project_id=manifest.id,
            outputs=manifest.outputs,
        )
        log_automation_event(
            "project_created",
            project_id=manifest.id,
            project_path=str(artifacts["project_path"]),
        )
        return AutomationGenerationResult(
            project_id=manifest.id,
            project_path=str(artifacts["project_path"]),
            manifest_path=str(artifacts["manifest_path"]),
            readme_path=str(artifacts["readme_path"]),
            entrypoint_path=str(artifacts["entrypoint_path"]),
            published_manifest_path=str(published_manifest),
            status="created",
            analysis=analysis,
        )

    @staticmethod
    def _analysis_from_manifest(manifest):
        return AutomationAnalysis(
            diagnostic="Manifesto aprovado pelo usuário.",
            viability="Manifesto validado.",
            inputs=[item.model_dump() for item in manifest.required_files],
            outputs=manifest.outputs,
            steps=manifest.steps,
            complexity="media" if len(manifest.required_files) > 1 else "baixa",
            project_id=manifest.id,
            project_name=manifest.name,
            category=manifest.category,
            description=manifest.description,
            project_path=manifest.project_path,
            entrypoint=manifest.entrypoint.script,
            timeout_seconds=manifest.timeout_seconds,
            manifest_data=manifest.model_dump(mode="json"),
        )

    @staticmethod
    def _publish_manifest(source_manifest: Path, project_id: str) -> Path:
        MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
        published_path = MANIFESTS_DIR / f"{project_id}.yaml"
        manifest_yaml = source_manifest.read_text(encoding="utf-8")
        published_path.write_text(manifest_yaml, encoding="utf-8")
        log_automation_event(
            "manifest_published",
            project_id=project_id,
            source_manifest=str(source_manifest),
            published_manifest=str(published_path),
        )
        return published_path