from core.ai_service import AIService, MockAIService
from core.logger import log_automation_event
from core.manifest_generator import ManifestGenerator
from core.models import (
    AutomationAnalysis,
    AutomationGenerationResult,
)
from core.project_scaffolder import ProjectScaffolder


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
        manifest = ManifestGenerator.validate(analysis.manifest_data)
        artifacts = ProjectScaffolder.create_automation_project(manifest)
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
            status="created",
            analysis=analysis,
        )