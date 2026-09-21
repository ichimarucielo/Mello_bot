# Padroes de Manifesto do MELLO BOT

## Finalidade

Este documento orienta o MELLO AI e novos integrantes a criar, revisar e validar manifestos compativeis com o runtime atual do MELLO BOT.

O manifesto e o contrato entre a plataforma e um ETL externo. Ele descreve qual projeto deve ser executado, qual script inicia o ETL, quais arquivos de entrada sao obrigatorios, como cada arquivo deve ser reconhecido e enviado ao ETL, quais outputs devem existir e quanto tempo a execucao pode durar.

A logica de negocio pertence ao projeto externo. O manifesto nao deve descrever transformacoes, regras de calculo ou etapas internas do ETL.

## Contrato suportado pelo runtime

O modelo oficial esta em `core/models.py`:

| Campo | Obrigatorio | Regra |
| --- | --- | --- |
| `id` | Sim | Identificador estavel, minusculo e sem espacos. |
| `name` | Sim | Nome legivel para o operador. |
| `category` | Sim | Categoria operacional curta. |
| `description` | Sim | Descricao objetiva do processamento. |
| `project_path` | Sim | Caminho do projeto ETL, normalmente relativo a raiz do MELLO BOT. |
| `timeout_seconds` | Nao | Inteiro maior que zero; padrao atual: `1800`. |
| `entrypoint.script` | Sim | Script relativo ao `project_path`. |
| `required_files` | Sim | Lista de arquivos de entrada e suas regras. |
| `outputs` | Sim | Lista de nomes de arquivos esperados. |
| `tags` | Nao | Lista de etiquetas para organizacao. Padrao: lista vazia. |
| `output_folder` | Nao | Pasta de outputs quando o ETL nao usa a pasta padrao. |

Nao adicionar campos de produto ou infraestrutura como `retry`, `schedule`, `triggers`, `workers`, `environments`, `notifications` ou `observability`. O Pydantic aceita campos extras atualmente, mas isso nao significa que o runtime implemente o comportamento deles.

## Template canonico

Use este modelo como ponto de partida. Substitua os valores de exemplo e nao remova campos obrigatorios.

```yaml
id: projeto_exemplo
name: Projeto Exemplo
category: operacional
description: Processamento dos arquivos de entrada para gerar o resultado final.
project_path: ../ProjetoExterno
timeout_seconds: 1800

entrypoint:
  script: src/main.py

required_files:
  - id: entrada
    display_name: Arquivo de entrada
    cli_argument: "--input-file"
    accepted_extensions:
      - csv
    required_columns:
      - ID

outputs:
  - resultado.xlsx

tags: []
```

O template acima e valido somente se `../ProjetoExterno/src/main.py` existir, aceitar `--input-file` e gerar `resultado.xlsx` no local esperado.

## Regras de caminho e execucao

- Considere a raiz do repositorio MELLO BOT ao validar caminhos.
- `project_path` aponta para a pasta do ETL externo.
- `entrypoint.script` e relativo a `project_path`, nao a raiz do MELLO BOT.
- O arquivo indicado por `entrypoint.script` precisa existir antes de uma execucao end-to-end.
- `cli_argument` precisa ser aceito pelo script do ETL. Nao invente o nome sem verificar o entrypoint ou documentar a hipotese.
- `outputs` deve conter nomes de arquivos, nao descricoes, tabelas ou pastas.
- `output_folder` deve ser usado quando os outputs ficam em uma pasta diferente da pasta de output padrao do projeto.
- `timeout_seconds` deve ser suficiente para o volume esperado. Sem evidencia, use `1800` e declare a hipotese.

## Arquivos de entrada

Cada item de `required_files` deve ser um objeto completo. O bloco abaixo e
apenas um fragmento para ilustrar essa secao, nao um manifesto independente:

```yaml
required_files:
  - id: vendas
    display_name: Vendas
    cli_argument: "--vendas"
    accepted_extensions:
      - csv
      - xlsx
    required_columns:
      - ID da venda
      - Valor
```

Regras:

- `id` identifica o papel do arquivo no contrato e deve ser estavel.
- `display_name` e o nome apresentado ao operador.
- `cli_argument` e o parametro enviado ao ETL.
- `accepted_extensions` deve usar somente `csv` ou `xlsx`.
- `required_columns` deve conter apenas colunas necessarias para reconhecer e validar o arquivo. Nao liste colunas por especulacao.
- Cada responsabilidade deve ter seu proprio arquivo. Prefira `sap`, `billing` e `prefeitura` a `arquivo1`, `arquivo2` e `arquivo3`.
- O nome fisico do upload nao substitui as regras de colunas e extensao.

O CSV atual e lido com separador `;`, tentando UTF-8 e depois latin1. XLSX e lido pelo Pandas/OpenPyXL. XLS nao deve ser declarado como suportado.

## Outputs

Declare todos os artefatos que precisam ser verificados depois da execucao:

```yaml
outputs:
  - conciliacao.xlsx
  - divergencias.xlsx
```

Boas declaracoes sao especificas, estaveis e verificaveis. Evite nomes vagos como `resultado.xlsx` quando o ETL produz varios artefatos, e evite nomes que contenham versoes acidentais como `resultado_final_definitivo_v7.xlsx`.

## Padroes de negocio

Os exemplos abaixo sao manifestos completos. Use-os como referencia de estrutura, nao copie nomes, colunas ou caminhos sem confirma-los.

### Conciliacao

Use para comparar duas ou mais bases e produzir divergencias.

```yaml
id: conciliacao_sap_billing
name: Conciliacao SAP x Billing
category: financeiro
description: Comparacao entre SAP e Billing para identificar divergencias.
project_path: ../ETL_CONCILIACAO
timeout_seconds: 1800
entrypoint:
  script: src/main.py
required_files:
  - id: sap
    display_name: SAP
    cli_argument: "--sap"
    accepted_extensions: [csv, xlsx]
    required_columns: [DOCUMENTO]
  - id: billing
    display_name: Billing
    cli_argument: "--billing"
    accepted_extensions: [csv, xlsx]
    required_columns: [DOCUMENTO]
outputs:
  - conciliacao.xlsx
  - divergencias.xlsx
tags: [conciliacao]
```

### Consolidacao

Use para juntar varios arquivos da mesma origem. Se o ETL aceita varios arquivos no mesmo argumento, confirme esse comportamento no entrypoint antes de modelar o manifesto. O contrato atual representa cada papel de entrada com um item em `required_files`.

```yaml
id: consolidacao_vendas
name: Consolidacao de Vendas
category: vendas
description: Consolidacao de arquivos de vendas em um unico dataset.
project_path: ../ETL_VENDAS
timeout_seconds: 1800
entrypoint:
  script: src/main.py
required_files:
  - id: vendas
    display_name: Arquivo de vendas
    cli_argument: "--vendas"
    accepted_extensions: [csv, xlsx]
    required_columns: [ID da venda, Valor]
outputs:
  - vendas_consolidadas.xlsx
tags: [consolidacao]
```

### Antifraude

Use para classificacao, saneamento ou score de risco.

```yaml
id: antifraude
name: Antifraude
category: risco
description: Tratamento e saneamento da base antifraude.
project_path: ../Antifraude_etl
output_folder: data/final
timeout_seconds: 1800
entrypoint:
  script: src/main.py
required_files:
  - id: base_antifraude
    display_name: Base Antifraude
    cli_argument: "--input-file"
    accepted_extensions: [xlsx]
    required_columns: [Child, MID, Product Description, Total Amount Due]
outputs:
  - antifraude_vf.xlsx
tags: [risco]
```

### Power BI

Use para preparar datasets consumidos por relatorios ou modelos analiticos. O formato do output deve ser confirmado pelo consumidor.

```yaml
id: dataset_power_bi
name: Dataset Power BI
category: power_bi
description: Preparacao do dataset para consumo no Power BI.
project_path: ../ETL_POWER_BI
timeout_seconds: 1800
entrypoint:
  script: src/main.py
required_files:
  - id: origem
    display_name: Base de origem
    cli_argument: "--input-file"
    accepted_extensions: [csv, xlsx]
    required_columns: [ID]
outputs:
  - dataset.csv
tags: [analytics]
```

### SAP e Salesforce

Para SAP, use identificadores de relatorio como `fs10n`, `fbl3n`, `zsd008` ou `zfaturamento` somente quando confirmados na origem. Para Salesforce, use um identificador como `salesforce` quando o arquivo representar essa fonte. Em ambos os casos, siga o template canonico e declare as colunas, argumentos e outputs reais.

## Processo do MELLO AI

Antes de gerar um manifesto, siga esta ordem:

1. Identifique o objetivo do ETL e escolha a categoria mais ampla adequada.
2. Liste cada arquivo de entrada e o papel que ele desempenha.
3. Obtenha os nomes reais das colunas e extensoes.
4. Confirme `project_path`, `entrypoint.script` e os argumentos aceitos pelo ETL.
5. Confirme os nomes e a pasta dos outputs.
6. Escolha `timeout_seconds` baseado no volume ou use `1800` como hipotese.
7. Gere o YAML usando o template canonico.
8. Valide a estrutura e os tipos contra `core/models.py`.
9. Declare hipoteses, informacoes ausentes e verificacoes pendentes.

Se faltar uma informacao critica, nao invente. Pergunte ou marque claramente:

> Hipotese: as colunas apresentadas sao exemplos e precisam ser confirmadas com a origem real dos dados antes da execucao.

## Checklist antes de salvar

- [ ] possui todos os campos obrigatorios;
- [ ] `id` e estavel, minusculo e sem espacos;
- [ ] `project_path` aponta para um projeto real ou esta marcado como pendente;
- [ ] `entrypoint.script` existe ou esta explicitamente pendente;
- [ ] cada `required_file` e um objeto completo;
- [ ] as extensoes sao somente `csv` ou `xlsx`;
- [ ] as colunas foram observadas ou estao marcadas como hipotese;
- [ ] cada `cli_argument` foi confirmado no ETL;
- [ ] `timeout_seconds` e inteiro maior que zero;
- [ ] todos os outputs sao nomes de arquivos verificaveis;
- [ ] `output_folder` foi declarado quando necessario;
- [ ] nao ha campos de runtime nao implementados;
- [ ] o YAML pode ser carregado sem erro;
- [ ] o manifesto passa por `Manifest.model_validate`.

## Exemplos invalidos

Nao gerar estruturas como estas:

```yaml
required_files:
  - base_a
  - base_b
```

O runtime espera objetos com `id`, `display_name`, `accepted_extensions` e `required_columns`.

```yaml
accepted_extensions:
  - xls
```

`xls` nao esta coberto pelo validador atual.

```yaml
entrypoint:
  script: main.py
project_path: C:/qualquer/lugar
```

Nao usar caminho absoluto sem necessidade operacional documentada. Alem disso, o script precisa existir dentro do projeto apontado.

```yaml
outputs:
  - resultado_final
```

O output deve ser um arquivo verificavel, normalmente com extensao.

## Criterio final de qualidade

Um manifesto bom:

- e valido no schema atual;
- descreve somente capacidades implementadas;
- e executavel sem alteracao no core quando os projetos externos existem;
- permite identificar os uploads sem depender apenas do nome do arquivo;
- declara outputs que podem ser verificados;
- explicita hipoteses e pendencias;
- mantem a logica de negocio no ETL externo.

Um manifesto nao esta pronto quando exige que a plataforma implemente filas, agendamento, retry, notificacoes, autenticacao ou regras de negocio que nao existem no runtime.
