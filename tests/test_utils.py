import pytest
import pandas as pd
import re
from core.utils import (
    normalize_key, 
    detect_key_type, 
    safe_merge, 
    standardize_column_names,
    validate_key_format,
    clean_dataframe
)

def test_normalize_key_cnpj_debug():
    """Testa normalização de CNPJ com debug"""
    # Dados com formatação
    series = pd.Series(['00.000.000/0001-00', '11.111.111/1111-11'])
    print(f"Original: {series.tolist()}")
    
    # Converte para string
    s = series.astype(str)
    print(f"Apos astype(str): {s.tolist()}")
    
    # Remove caracteres não numéricos
    s = s.apply(lambda x: re.sub(r'[^\d]', '', x.strip()))
    print(f"Apos regex: {s.tolist()}")
    
    # Normaliza como CNPJ
    result = normalize_key(s, 'cnpj')
    print(f"Resultado final: {result.tolist()}")
    
    # Verifica resultado
    assert result.iloc[0] == '00000000000100'
    assert result.iloc[1] == '11111111111111'

def test_normalize_key_cnpj():
    """Testa normalização de CNPJ"""
    # Dados com formatação
    series = pd.Series(['00.000.000/0001-00', '11.111.111/1111-11'])
    
    # Normaliza como CNPJ
    result = normalize_key(series, 'cnpj')
    
    # Verifica resultado
    assert result.iloc[0] == '00000000000100'
    assert result.iloc[1] == '11111111111111'
    assert all(len(x) == 14 for x in result)

def test_normalize_key_cpf():
    """Testa normalização de CPF"""
    # Dados com formatação
    series = pd.Series(['000.000.000-00', '111.111.111-11'])
    
    # Normaliza como CPF
    result = normalize_key(series, 'cpf')
    
    # Verifica resultado
    assert result.iloc[0] == '00000000000'
    assert result.iloc[1] == '11111111111'
    assert all(len(x) == 11 for x in result)

def test_normalize_key_preserves_missing_values_and_generic_ids():
    cnpj_values = pd.Series(['00.000.000/0001-00', 123.0, None])

    result = normalize_key(cnpj_values, 'cnpj')

    assert result.iloc[0] == '00000000000100'
    assert result.iloc[1] == '00000000000123'
    assert pd.isna(result.iloc[2])
    assert normalize_key(pd.Series(['123']), 'default').iloc[0] == '123'

def test_detect_key_type():
    """Testa detecção de tipo de chave"""
    # Testa CNPJ
    assert detect_key_type('CNPJ') == 'cnpj'
    assert detect_key_type('cnpj') == 'cnpj'
    assert detect_key_type('inscricao') == 'cnpj'
    
    # Testa CPF
    assert detect_key_type('cpf') == 'cpf'
    
    # Testa outros
    assert detect_key_type('nome') is None
    assert detect_key_type('id') is None

def test_safe_merge():
    """Testa merge seguro"""
    # Dataframes de teste
    left = pd.DataFrame({'id': [1, 2], 'nome': ['a', 'b']})
    right = pd.DataFrame({'id': [2, 3], 'valor': [10, 20]})
    left_before = left.copy(deep=True)
    right_before = right.copy(deep=True)
    
    # Realiza merge com how='outer' para trazer todos os registros
    result = safe_merge(left, right, on='id', how='outer')
    
    # Verifica resultado
    assert len(result) == 3
    assert 'nome' in result.columns
    assert 'valor' in result.columns
    pd.testing.assert_frame_equal(left, left_before)
    pd.testing.assert_frame_equal(right, right_before)

def test_standardize_column_names():
    """Testa padronização de nomes de colunas"""
    # DataFrame com nomes inconsistentes
    df = pd.DataFrame({
        'Nome Completo': ['João', 'Maria'],
        'IDADE': [25, 30],
        'Data de Nascimento': ['1990-01-01', '1995-02-02']
    })
    
    # Padroniza nomes
    result = standardize_column_names(df)
    
    # Verifica resultado
    expected_columns = ['nome_completo', 'idade', 'data_de_nascimento']
    assert list(result.columns) == expected_columns

def test_validate_key_format():
    """Testa validação de formato de chave"""
    # Testa CNPJ válido
    assert validate_key_format('00.000.000/0001-00', 'cnpj') == True
    assert validate_key_format('00000000000001', 'cnpj') == True
    
    # Testa CNPJ inválido
    assert validate_key_format('00.000.000/0001-0', 'cnpj') == False
    assert validate_key_format('abc', 'cnpj') == False
    
    # Testa CPF válido
    assert validate_key_format('000.000.000-00', 'cpf') == True
    assert validate_key_format('00000000000', 'cpf') == True

def test_clean_dataframe():
    """Testa limpeza de dataframe"""
    # DataFrame com espaços e nulos
    df = pd.DataFrame({
        'nome': ['  João  ', 'Maria', '  '],
        'idade': [25, None, 30],
        'valor': ['100', '200', '300']
    })
    
    # Limpa dataframe
    result = clean_dataframe(df)
    
    # Verifica resultado
    assert '  João  ' not in result['nome'].values
    assert result['nome'].notna().all()
