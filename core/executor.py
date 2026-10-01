import subprocess
import sys
from datetime import datetime
from pathlib import Path

from core.enums import ExecutionStatus
from core.exceptions import TimeoutExecutionError
from core.logger import log_execution_failure, log_execution_start, log_execution_success
from core.manifest_loader import load_manifest
from core.models import ExecutionResult
from core.settings import BASE_DIR
from core.template_engine import TemplateEngine

# Importando a validação inteligente que criamos no passo anterior
# from core.validators import validate_input_file, MVPInputError


class Executor:

    @staticmethod
    def _parse_subprocess_error(stderr: str) -> str:
        """
        Traduz erros técnicos de bibliotecas (Pandas, etc) em mensagens 
        amigáveis para o usuário do MVP.
        """
        stderr_lower = stderr.lower()
        
        # Erros comuns de leitura de CSV no Pandas
        if "unicodedecodeerror" in stderr_lower:
            return "Erro de codificação: O arquivo não está em UTF-8. Verifique o formato do arquivo (tente salvar como CSV UTF-8)."
        if "parsererror" in stderr_lower or "error tokenizing data" in stderr_lower:
            return "Erro de formatação: O arquivo CSV parece estar com o separador incorreto ou com quebras de linha fora do padrão."
        if "keyerror" in stderr_lower or "ufunc 'isnan' not supported" in stderr_lower:
            # Tenta extrair a coluna que faltou do erro do pandas
            import re
            match = re.search(r"KeyError:\s*['\"](.+?)['\"]", stderr)
            col_name = match.group(1) if match else "desconhecida"
            return f"Erro de Schema: A coluna obrigatória '{col_name}' não foi encontrada no arquivo."
        if "filenotfounderror" in stderr_lower:
            return "Erro: O sistema tentou ler um arquivo que não existe no servidor. O upload pode ter falhado."
            
        # Fallback: Se for um erro não mapeado, esconde o traceback do usuário
        # mas mantém no log para o dev investigar.
        return "Ocorreu um erro inesperado ao processar o arquivo. A equipe técnica foi notificada."

    @staticmethod
    def run(
        project_id: str,
        files: dict[str, str],
    ) -> ExecutionResult:

        started_at = datetime.now()
        manifest = load_manifest(project_id)
        timeout_seconds = getattr(manifest, "timeout_seconds", 1800)

        project_path = (
            BASE_DIR /
            manifest.project_path
        ).resolve()

        script_path = (
            project_path /
            manifest.entrypoint.script
        ).resolve()
        try:
            script_path.relative_to(project_path)
        except ValueError as error:
            raise ValueError("O entrypoint precisa estar dentro da pasta do projeto.") from error
        if not script_path.is_file():
            raise FileNotFoundError(f"Entrypoint não encontrado: {script_path}")

        if manifest.required_files and not files:
            raise ValueError("O projeto requer um arquivo de entrada, mas nenhum foi enviado.")

        log_execution_start(
            execution_id=None,
            project_id=project_id,
            duration=0,
            uploaded_files=list(files.keys()),
            status="running",
            timeout_seconds=timeout_seconds,
        )

        args = [
            sys.executable,
            manifest.entrypoint.script,
        ]

        for required_file in manifest.required_files:
            cli_argument = required_file.cli_argument
            if not cli_argument:
                continue

            file_path = files.get(required_file.id)
            if not file_path:
                # Erro amigável
                raise ValueError(f"Arquivo obrigatório não enviado: {required_file.id}")

            if not Path(file_path).exists():
                # Erro amigável
                raise FileNotFoundError(
                    f"Arquivo de entrada obrigatório '{required_file.id}' não encontrado: {file_path}"
                )

            # ==============================================
            # AQUI ENTRA O FAIL-FAST (Validação antes de rodar)
            # ==============================================
            # if required_file.id == "clientes_csv": # Exemplo de validação específica
            #     try:
            #         validate_input_file(file_path, required_columns=["ID", "DATA", "VALOR"])
            #     except MVPInputError as e:
            #         raise ValueError(str(e)) from e # Transforma em erro de validação amigável

            args.extend([
                cli_argument,
                file_path,
            ])

        try:
            result = subprocess.run(
                args,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            duration_seconds = round((datetime.now() - started_at).total_seconds(), 2)
            log_execution_failure(
                execution_id=None,
                project_id=project_id,
                duration=duration_seconds,
                uploaded_files=list(files.keys()),
                exception=TimeoutExecutionError(project_id, timeout_seconds),
                status="timeout",
            )
            raise TimeoutExecutionError(project_id, timeout_seconds) from error

        duration_seconds = round((datetime.now() - started_at).total_seconds(), 2)

        if result.returncode != 0:
            # ==============================================
            # A MÁGICA ACONTECE AQUI: Traduzir o STDERR
            # ==============================================
            raw_error = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            
            # Mensagem que o usuário vai ver (amigável)
            user_friendly_error = Executor._parse_subprocess_error(result.stderr)

            log_execution_failure(
                execution_id=None,
                project_id=project_id,
                duration=duration_seconds,
                uploaded_files=list(files.keys()),
                exception=raw_error, # Log mantém o traceback completo para o Dev
                status="failed",
            )
            return ExecutionResult(
                execution_id="",
                project_id=project_id,
                status=ExecutionStatus.FAILED,
                duration_seconds=duration_seconds,
                error_message=user_friendly_error, # Usuário vê a mensagem traduzida
            )

        log_execution_success(
            execution_id=None,
            project_id=project_id,
            duration=duration_seconds,
            uploaded_files=list(files.keys()),
            outputs=[],
            status="success",
        )

        return ExecutionResult(
            execution_id="",
            project_id=project_id,
            status=ExecutionStatus.SUCCESS,
            duration_seconds=duration_seconds,
        )
