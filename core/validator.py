import chardet
import pandas as pd
from pathlib import Path

from core.column_normalizer import normalize_column
from core.models import RequiredFile


class Validator:

    @staticmethod
    def _detect_encoding(file_path: Path) -> str:
        """Detecta o encoding do arquivo lendo uma amostra inicial."""
        try:
            with open(file_path, 'rb') as f:
                # Lê os primeiros 100KB para ser rápido
                raw_data = f.read(100_000)
            result = chardet.detect(raw_data)
            # Confiança baixa (ex: ascii vs utf8), damos preferência para utf-8
            if result.get('confidence', 0) < 0.7:
                return 'utf-8'
            return result.get('encoding', 'utf-8') or 'utf-8'
        except Exception:
            return 'utf-8'

    @staticmethod
    def _read_csv_robust(file_path: Path, nrows: int = 0) -> pd.DataFrame:
        """
        Tenta ler o CSV de forma inteligente, testando encodings e separadores.
        Levanta ValueError com mensagem amigável se falhar.
        """
        detected_enc = Validator._detect_encoding(file_path)
        
        # Ordem de prioridade de encodings (evita duplicatas)
        encodings_to_try = list(dict.fromkeys([
            detected_enc, 'utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1'
        ]))
        
        # Separadores comuns no mundo corporativo brasileiro
        separators_to_try = [';', ',', '|', '\t']

        last_error = None

        for enc in encodings_to_try:
            for sep in separators_to_try:
                try:
                    df = pd.read_csv(
                        file_path,
                        nrows=nrows,
                        encoding=enc,
                        sep=sep,
                        engine='python' # engine python lida melhor com sep variável
                    )
                    
                    # Verificação de sanidade:
                    # Se achou só 1 coluna e o arquivo tem conteúdo, o separador está errado.
                    # (Ex: arquivo separado por ; foi lido com ,)
                    if len(df.columns) == 1 and nrows == 0:
                        # Tenta ler 5 linhas para ver se o problema persiste
                        df_check = pd.read_csv(file_path, nrows=5, encoding=enc, sep=sep, engine='python')
                        if len(df_check.columns) == 1 and file_path.stat().st_size > 100:
                            continue # Separador errado, tenta o próximo
                    
                    return df

                except UnicodeDecodeError:
                    continue # Encoding errado, tenta o próximo
                except pd.errors.EmptyDataError:
                    raise ValueError(f"O arquivo está vazio: {file_path.name}")
                except pd.errors.ParserError as e:
                    last_error = e
                    continue # Arquivo quebrou no meio, talvez o separador esteja errado
                except Exception as e:
                    last_error = e
                    continue

        # Fallback desesperado: E se for um Excel renomeado para .csv?
        try:
            df = pd.read_excel(file_path, nrows=nrows)
            return df
        except Exception:
            pass # Ignora, o erro original de CSV é mais relevante

        # Se chegou aqui, nada funcionou. Lança erro amigável.
        raise ValueError(
            f"Não foi possível ler o arquivo CSV '{file_path.name}'. "
            "Verifique se o separador está correto (ex: ponto e vírgula) ou se o arquivo não está corrompido."
        )

    @staticmethod
    def get_columns(file_path: Path) -> list:
        extension = file_path.suffix.lower()

        if extension == ".csv":
            df = Validator._read_csv_robust(file_path, nrows=0)
            
            columns = list(df.columns)
            if not columns:
                raise ValueError(f"O arquivo CSV não possui colunas válidas: {file_path.name}")
            
            # Limpa espaços extras nos nomes das colunas que o Pandas às vezes deixa
            return [col.strip() for col in columns]

        if extension in [".xlsx", ".xls"]:
            try:
                df = pd.read_excel(file_path, nrows=0)
            except Exception as error:
                raise ValueError(
                    f"Não foi possível ler o arquivo Excel '{file_path.name}'. Ele pode estar corrompido."
                ) from error

            columns = list(df.columns)
            if not columns:
                raise ValueError(f"O arquivo Excel não possui colunas válidas: {file_path.name}")
            
            return [col.strip() for col in columns]

        raise ValueError(
            f"Formato de arquivo não suportado ('{extension}'). Use .csv, .xlsx ou .xls."
        )

    @classmethod
    def validate_columns(
        cls,
        file_path: Path,
        required_columns: list[str]
    ) -> dict:

        # Aqui o erro amigável de leitura já pode estourar
        original_columns = cls.get_columns(file_path)

        normalized_columns = {
            normalize_column(column)
            for column in original_columns
        }

        missing_columns = []

        for column in required_columns:

            normalized_required = normalize_column(column)

            if normalized_required not in normalized_columns:
                missing_columns.append(column)

        valid = len(missing_columns) == 0

        score = (
            100
            if valid
            else int(
                (
                    (
                        len(required_columns) - len(missing_columns)
                    ) / len(required_columns)
                ) * 100
            )
        )

        return {
            "valid": valid,
            "score": score,
            "columns_found": original_columns,
            "missing_columns": missing_columns
        }

    @classmethod
    def validate_file(
        cls,
        file_path: Path,
        file_definition: RequiredFile
    ) -> dict:

        validation_result = cls.validate_columns(
            file_path=file_path,
            required_columns=file_definition.required_columns
        )
        critical_result = (
            cls.validate_columns(
                file_path=file_path,
                required_columns=file_definition.critical_columns,
            )
            if file_definition.critical_columns
            else {
                "valid": True,
                "score": 100,
                "missing_columns": [],
            }
        )

        return {
            "file_id": file_definition.id,
            "display_name": file_definition.display_name,
            "confidence_score": min(
                validation_result["score"],
                critical_result["score"],
            ),
            "critical_columns": file_definition.critical_columns,
            "missing_critical_columns": critical_result["missing_columns"],
            "critical_columns_valid": critical_result["valid"],
            **validation_result
        }
