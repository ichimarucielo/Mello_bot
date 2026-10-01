import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Importa e roda o pytest
import pytest
if __name__ == "__main__":
    pytest.main([str(project_root / "tests"), "-v"])
