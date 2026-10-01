import re
import pandas as pd
from typing import Union, Optional, List, Dict, Any, Literal
import logging

logger = logging.getLogger(__name__)

def normalize_key(series: pd.Series, key_type: str = 'default') -> pd.Series:
    """
    Padroniza colunas chave (CNPJ, CPF, etc.) para string sem formatação.
    Resolve o erro: ValueError: You are trying to merge on int64 and str columns.
    """
    lengths = {'cnpj': 14, 'cpf': 11}
    expected_length = lengths.get(key_type)

    def normalize(value: Any) -> Any:
        if pd.isna(value):
            return pd.NA

        if isinstance(value, float):
            if not value.is_integer():
                return pd.NA
            value = int(value)

        raw = str(value).strip()
        if not expected_length:
            return raw

        digits = re.sub(r'[^\d]', '', raw)
        if expected_length and digits and len(digits) <= expected_length:
            return digits.zfill(expected_length)
        return digits

    return series.map(normalize)

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa um DataFrame removendo espaços em branco e valores nulos.
    """
    df = df.copy()
    
    # Remove espaços em branco de strings
    for col in df.columns:
        if (
            pd.api.types.is_object_dtype(df[col].dtype)
            or pd.api.types.is_string_dtype(df[col].dtype)
        ):
            df[col] = df[col].astype('string').str.strip()
    
    # Remove linhas completamente nulas
    df = df.dropna(how='all')
    
    return df

def validate_key_format(key: str, key_type: str) -> bool:
    """
    Valida se uma chave está no formato correto.
    """
    # Remove formatação
    cleaned = re.sub(r'[^\d]', '', str(key))
    
    if key_type == 'cnpj':
        return len(cleaned) == 14 and cleaned.isdigit()
    elif key_type == 'cpf':
        return len(cleaned) == 11 and cleaned.isdigit()
    return True

def safe_merge(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    on: Union[str, List[str]],
    how: Literal['inner', 'left', 'right', 'outer'] = 'inner',
    key_types: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    Realiza merge seguro entre DataFrames, normalizando chaves se necessário.
    """
    if isinstance(on, str):
        on = [on]

    left_df = left_df.copy()
    right_df = right_df.copy()
    
    # Normaliza chaves se necessário
    if key_types:
        for key in on:
            if key in key_types:
                logger.info(f"Normalizando chave '{key}' como {key_types[key]}")
                left_df[key] = normalize_key(left_df[key], key_types[key])
                right_df[key] = normalize_key(right_df[key], key_types[key])
    
    # Realiza o merge
    return pd.merge(left_df, right_df, on=on, how=how)


def reconcile_dataframes(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    key: str | list[str] | None,
) -> pd.DataFrame:
    """Merge duas bases e classifica correspondências e registros sem chave."""
    left = left_df.copy()
    right = right_df.copy()
    key_columns = [key] if isinstance(key, str) else list(key or [])
    if not key_columns:
        raise ValueError("A chave de conciliação não foi definida.")

    missing_columns = [
        column for column in key_columns
        if column not in left.columns or column not in right.columns
    ]
    if missing_columns:
        raise KeyError(
            f"Chaves ausentes nas bases: {', '.join(missing_columns)}"
        )

    if not all(
        column in left.columns and column in right.columns
        for column in key_columns
    ):
        raise ValueError("As chaves de conciliação não existem nas duas bases.")

    for column in key_columns:
        key_type = detect_key_type(column) or "default"
        left[column] = normalize_key(left[column], key_type)
        right[column] = normalize_key(right[column], key_type)

    left_has_key = left[key_columns].notna().all(axis=1)
    right_has_key = right[key_columns].notna().all(axis=1)
    for column in key_columns:
        left_has_key &= left[column].ne("")
        right_has_key &= right[column].ne("")
    merged = pd.merge(
        left.loc[left_has_key],
        right.loc[right_has_key],
        on=key_columns,
        how="outer",
        indicator=True,
        suffixes=("_left", "_right"),
    )
    merged["status"] = merged.pop("_merge").map(
        {"both": "match", "left_only": "left_only", "right_only": "right_only"}
    )

    left_without_key = left.loc[~left_has_key].merge(
        right.iloc[0:0],
        on=key_columns,
        how="left",
        suffixes=("_left", "_right"),
    )
    left_without_key["status"] = "left_only"
    right_without_key = left.iloc[0:0].merge(
        right.loc[~right_has_key],
        on=key_columns,
        how="right",
        suffixes=("_left", "_right"),
    )
    right_without_key["status"] = "right_only"

    return pd.concat(
        [merged, left_without_key, right_without_key],
        ignore_index=True,
    )

def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza nomes de colunas para snake_case.
    """
    df = df.copy()
    df.columns = [
        str(col)
        .lower()
        .replace(' ', '_')
        .replace('-', '_')
        .replace('.', '_')
        .replace('/', '_')
        for col in df.columns
    ]
    return df

def detect_key_type(key_name: str) -> Optional[str]:
    """
    Detecta o tipo de chave pelo nome.
    """
    key_lower = str(key_name).lower()
    if any(term in key_lower for term in ['cnpj', 'inscricao']):
        return 'cnpj'
    elif any(term in key_lower for term in ['cpf']):
        return 'cpf'
    return None

def prepare_for_merge(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    key_columns: List[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepara dois DataFrames para merge, normalizando chaves detectadas.
    """
    left_df = left_df.copy()
    right_df = right_df.copy()
    
    for key in key_columns:
        # Detecta tipo da chave
        key_type = detect_key_type(key)
        if key_type:
            logger.info(f"Chave '{key}' detectada como {key_type}")
            left_df[key] = normalize_key(left_df[key], key_type)
            right_df[key] = normalize_key(right_df[key], key_type)
    
    return left_df, right_df
