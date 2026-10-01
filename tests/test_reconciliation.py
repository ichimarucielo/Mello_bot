import pytest
import pytest
import pandas as pd
from core.utils import reconcile_dataframes

def execute_reconciliation(left_df, right_df, key):
    return reconcile_dataframes(left_df, right_df, key)

def test_reconciliation_with_cnpj():
    """Testa reconciliação com CNPJ formatado"""
    left_df = pd.DataFrame({
        'CNPJ': ['00.000.000/0001-00', '11.111.111/1111-11'],
        'valor': [100, 200]
    })
    
    right_df = pd.DataFrame({
        'CNPJ': ['00000000000100', '11111111111111'],
        'valor': [150, 250]
    })
    
    # Executa reconciliação
    result = execute_reconciliation(left_df, right_df, 'CNPJ')
    
    # Verifica resultado
    assert len(result) == 2
    assert 'status' in result.columns
    assert (result['status'] == 'match').all()

def test_reconciliation_with_missing_records():
    """Testa reconciliação com registros faltantes"""
    left_df = pd.DataFrame({
        'CNPJ': ['00.000.000/0001-00', '11.111.111/1111-11'],
        'valor': [100, 200]
    })
    
    right_df = pd.DataFrame({
        'CNPJ': ['00000000000100'],  # Falta o segundo CNPJ
        'valor': [150]
    })
    
    # Executa reconciliação
    result = execute_reconciliation(left_df, right_df, 'CNPJ')
    
    # Verifica resultado
    assert len(result) == 2
    assert (result['status'] == 'match').sum() == 1
    assert (result['status'] == 'left_only').sum() == 1


def test_missing_cnpj_values_never_match_each_other():
    left_df = pd.DataFrame({'CNPJ': [None], 'valor': [100]})
    right_df = pd.DataFrame({'CNPJ': [None], 'valor': [150]})

    result = execute_reconciliation(left_df, right_df, 'CNPJ')

    assert result['status'].value_counts().to_dict() == {
        'left_only': 1,
        'right_only': 1,
    }


def test_composite_key_normalizes_cnpj_and_numeric_identifier():
    left_df = pd.DataFrame(
        {'CNPJ': ['00.000.000/0001-00'], 'Documento': ['1'], 'valor': [100]}
    )
    right_df = pd.DataFrame(
        {'CNPJ': ['00000000000100'], 'Documento': [1.0], 'valor': [150]}
    )

    result = reconcile_dataframes(left_df, right_df, ['CNPJ', 'Documento'])

    assert result['status'].tolist() == ['match']


def test_missing_declared_key_does_not_fall_back_to_another_column():
    left_df = pd.DataFrame({'DOCUMENTO': ['1']})
    right_df = pd.DataFrame({'DOCUMENTO': ['1']})

    with pytest.raises(KeyError, match="CNPJ"):
        reconcile_dataframes(left_df, right_df, 'CNPJ')
