import pandas as pd
from core.models import Manifest
from core.template_engine import TemplateEngine
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
    assert 'valor_left' in result.columns
    assert 'valor_right' in result.columns

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
    assert (result['status'] == 'right_only').sum() == 0


def test_rendered_reconciliation_template_executes_cnpj_rule():
    manifest = Manifest.model_validate(
        {
            'id': 'reconciliation-test',
            'name': 'Reconciliation Test',
            'category': 'financeiro',
            'description': 'Teste do template de reconciliação',
            'project_path': 'projects/reconciliation-test',
            'entrypoint': {'script': 'src/main.py'},
            'required_files': [
                {
                    'id': 'left',
                    'display_name': 'Base esquerda',
                    'accepted_extensions': ['csv'],
                    'required_columns': ['CNPJ'],
                    'cli_argument': '--left',
                },
                {
                    'id': 'right',
                    'display_name': 'Base direita',
                    'accepted_extensions': ['csv'],
                    'required_columns': ['CNPJ'],
                    'cli_argument': '--right',
                },
            ],
            'outputs': ['conciliacao.xlsx'],
        }
    )
    source = TemplateEngine.render_pattern_main(manifest, 'reconciliation')
    namespace = {'__name__': 'generated_reconciliation_test'}
    exec(compile(source, '<generated-reconciliation>', 'exec'), namespace)

    result = namespace['reconcile'](
        pd.DataFrame({'CNPJ': ['00.000.000/0001-00']}),
        pd.DataFrame({'CNPJ': ['00000000000100']}),
        'CNPJ',
    )

    assert result['status'].tolist() == ['match']
