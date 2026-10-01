import pandas as pd
from core.utils import normalize_key

# Teste manual
series = pd.Series(['00.000.000/0001-00'])
result = normalize_key(series, 'cnpj')
print(f"Resultado: {result.tolist()}")
print(f"Esperado: ['00000000000100']")
print(f"Correto: {result.iloc[0] == '00000000000100'}")
