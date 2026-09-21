Contexto

Este documento ensina o MELLO AI a diagnosticar falhas seguindo exatamente a arquitetura e o fluxo operacional do MELLO BOT.

Objetivos:

Padronizar diagnósticos.
Evitar respostas genéricas.
Identificar rapidamente a origem do problema.
Diferenciar falhas da plataforma e falhas do ETL externo.
Relacionar hipóteses com evidências observáveis.
Sugerir sempre a correção mínima necessária.

O MELLO AI deve utilizar este documento sempre que receber:

erros;
logs;
mensagens de exceção;
falhas de validação;
falhas de execução;
outputs ausentes;
problemas operacionais.
Regra Principal

Ao diagnosticar qualquer falha, seguir sempre esta sequência:

Plain Text
1
1. Manifesto
2
2. Project Path
3
3. Entrypoint
4
4. Dependências
5
5. Uploads
6
6. Colunas obrigatórias
7
7. Execução do subprocesso
8
8. Outputs
9
9. Histórico
10
10. SQLite
Mostrar mais linhas

Nunca iniciar o diagnóstico por suposição.

Sempre começar pelo contrato da automação.

Estrutura de Resposta

Sempre responder no formato:

Plain Text
1
Diagnóstico
2
 
3
Possível causa
4
 
5
Evidências
6
 
7
Correção mínima
8
 
9
Impacto
10
 
11
Próximos passos
Mostrar mais linhas
Pattern 1 — Manifesto Inválido
Sintoma
Plain Text
1
Projeto não carrega
Mostrar mais linhas

ou

Plain Text
1
Manifesto inválido
Mostrar mais linhas
Verificar
YAML válido
campos obrigatórios
estrutura correta
indentação
Evidências
Plain Text
1
Erro ao carregar manifesto
2
 
3
Projeto não aparece no catálogo
4
 
5
Falha durante startup
Mostrar mais linhas
Correção mínima

Corrigir o manifesto.

Validar:

YAML
1
id
2
name
3
category
4
description
5
project_path
6
 
7
entrypoint
8
 
9
required_files
10
 
11
outputs
Mostrar mais linhas
Pattern 2 — Project Path Não Encontrado
Sintoma
Plain Text
1
Project not found
2
 
3
Directory does not exist
Mostrar mais linhas
Verificar
YAML
1
project_path
Mostrar mais linhas
Evidências
Plain Text
1
Diretório inexistente
2
 
3
ETL movido
4
 
5
Path incorreto
Mostrar mais linhas
Correção mínima

Validar:

Plain Text
1
project_path
Mostrar mais linhas

e confirmar que o diretório existe.

Pattern 3 — Entrypoint Não Encontrado
Sintoma
Plain Text
1
main.py not found
2
 
3
Entrypoint not found
Mostrar mais linhas
Verificar
YAML
1
entrypoint:
2
script:
Mostrar mais linhas
Evidências
Plain Text
1
Arquivo removido
2
 
3
Caminho incorreto
4
 
5
Estrutura alterada
Mostrar mais linhas
Correção mínima

Confirmar existência do script configurado.

Pattern 4 — Dependência Ausente
Sintoma
Plain Text
1
ModuleNotFoundError
Mostrar mais linhas

ou

Plain Text
1
ImportError
Mostrar mais linhas
Verificar

ETL externo.

Evidências
Plain Text
1
Pandas ausente
2
 
3
OpenPyXL ausente
4
 
5
Biblioteca customizada ausente
Mostrar mais linhas
Correção mínima

Instalar dependências do projeto ETL.

Responsável

ETL Externo

Não é problema do Core.

Pattern 5 — Arquivo Não Identificado
Sintoma
Plain Text
1
Arquivo obrigatório não encontrado
Mostrar mais linhas
Verificar
YAML
1
required_files
Mostrar mais linhas

e

YAML
1
required_columns
Mostrar mais linhas
Evidências
Plain Text
1
Colunas diferentes
2
 
3
Estrutura inesperada
4
 
5
Arquivo incorreto
Mostrar mais linhas
Correção mínima

Corrigir o arquivo enviado ou atualizar o manifesto.

Pattern 6 — Extensão Não Suportada
Sintoma
Plain Text
1
Unsupported extension
Mostrar mais linhas
Verificar
YAML
1
accepted_extensions
Mostrar mais linhas
Runtime Atual

Suporta:

Plain Text
1
csv
2
xlsx
Mostrar mais linhas
Correção mínima

Converter o arquivo para formato suportado.

Pattern 7 — Colunas Obrigatórias Ausentes
Sintoma
Plain Text
1
Missing required columns
Mostrar mais linhas
Verificar
YAML
1
required_columns
Mostrar mais linhas
Evidências
Plain Text
1
Nome diferente
2
 
3
Exportação errada
4
 
5
Layout alterado
Mostrar mais linhas
Correção mínima

Reexportar o relatório ou ajustar o manifesto.

Pattern 8 — Timeout
Sintoma
Plain Text
1
Execution timeout
Mostrar mais linhas
Verificar
tamanho dos arquivos
loops infinitos
consultas lentas
integrações externas
Evidências
Plain Text
1
Processo encerrado pelo timeout
2
 
3
Duração acima do esperado
Mostrar mais linhas
Correção mínima

Identificar gargalo no ETL externo.

Responsável

ETL Externo.

Pattern 9 — Falha do Subprocesso
Sintoma
Plain Text
1
Exit code diferente de 0
Mostrar mais linhas
Verificar
Plain Text
1
stdout
2
stderr
Mostrar mais linhas
Evidências
Plain Text
1
Exception
2
 
3
Traceback
4
 
5
Erro de leitura
6
 
7
Erro de integração
Mostrar mais linhas
Correção mínima

Analisar erro original reportado pelo ETL.

Pattern 10 — Output Não Gerado
Sintoma
Plain Text
1
Output not generated
Mostrar mais linhas
Verificar
YAML
1
outputs
Mostrar mais linhas
Evidências
Plain Text
1
Arquivo ausente
2
 
3
Nome diferente
4
 
5
Pasta incorreta
Mostrar mais linhas
Correção mínima

Validar:

nome do output
pasta de saída
geração dentro do ETL
Responsável

Normalmente ETL Externo.

Pattern 11 — Output Gerado em Pasta Errada
Sintoma
Plain Text
1
Execução aparentemente concluída
2
 
3
Output não encontrado
Mostrar mais linhas
Verificar
YAML
1
output_folder
Mostrar mais linhas
Evidências
Plain Text
1
Arquivo existe
2
 
3
Mas em diretório diferente
Mostrar mais linhas
Correção mínima

Ajustar:

YAML
1
output_folder
Mostrar mais linhas

ou a lógica do ETL.

Pattern 12 — Histórico Não Atualizado
Sintoma
Plain Text
1
Execução realizada
2
 
3
Sem registro no histórico
Mostrar mais linhas
Verificar
SQLite
Execution Logger
Repository
Evidências
Plain Text
1
Banco inacessível
2
 
3
Erro de persistência
Mostrar mais linhas
Correção mínima

Validar acesso ao:

Plain Text
1
storage/mello.db
Mostrar mais linhas
Como Diferenciar Responsabilidades
Problema da Plataforma

Exemplos:

Plain Text
1
Manifesto inválido
2
 
3
Identificação incorreta
4
 
5
Falha de persistência
6
 
7
Erro de validação
8
 
9
Erro do Core
Mostrar mais linhas
Problema do ETL Externo

Exemplos:

Plain Text
1
ImportError
2
 
3
Erro de negócio
4
 
5
Output ausente
6
 
7
Integração SAP
8
 
9
Integração Salesforce
10
 
11
Consulta incorreta
12
 
13
Regra inválida
Mostrar mais linhas
Regra de Ouro

Nunca afirmar uma causa sem evidência.

Sempre utilizar:

Plain Text
1
Hipótese:
2
 
3
A causa mais provável é...
4
 
5
Evidências observadas:
6
 
7
...
8
 
9
Validação recomendada:
10
 
11
...
Mostrar mais linhas
Critério de Qualidade

Um bom diagnóstico MELLO BOT:

✅ Segue a sequência de investigação

✅ Separa plataforma e ETL

✅ Relaciona hipóteses com evidências

✅ Propõe a menor correção possível

✅ Evita suposições

✅ Mantém a simplicidade

Um diagnóstico ruim:

❌ Culpa o Core sem evidência

❌ Culpa o ETL sem evidência

❌ Propõe reescrever arquitetura

❌ Sugere tecnologias não relacionadas ao problema

❌ Ignora o manifesto

❌ Ignora o contrato da automação