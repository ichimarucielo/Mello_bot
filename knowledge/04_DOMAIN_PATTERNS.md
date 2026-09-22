# Padroes de dominio do MELLO BOT

## Finalidade

Este documento orienta o Automation Designer a interpretar termos de negocio e gerar manifestos mais precisos. As regras sao deterministicas: primeiro identificam a origem e o dominio, depois escolhem extensoes, inputs, categoria, padrao de automacao e outputs.

A identificacao de um dominio nao substitui a validacao dos arquivos reais. Colunas listadas aqui sao referencias comuns e devem ser confirmadas antes da execucao.

## Regras de precedencia

1. Identifique relatorios SAP por nome tecnico antes de aplicar inferencias genericas.
2. Se o prompt contiver `FS10N`, `FBL3N`, `FBL5N` ou `ZSD008`, classifique `fonte = SAP`, `categoria = financeiro` e `extensao preferencial = xlsx`.
3. Nao assuma CSV para relatorios SAP.
4. `Billing` e uma origem/aplicacao propria. Nao o transforme automaticamente em `faturamento`.
5. `Faturamento` descreve um processo de negocio; `Billing` identifica uma fonte especifica quando essa palavra aparece.
6. `Prefeitura` e uma origem municipal diferente de SAP, mesmo quando os dois aparecem no mesmo processo.
7. Quando houver duas fontes e termos de comparacao, conciliacao ou divergencia, prefira o padrao de conciliacao.
8. Se nao houver sinais suficientes, use os fallbacks genericos do runtime e declare a hipotese.

## File Entity Detection

Antes de classificar a origem, responda: quantos arquivos o usuario descreveu?

Uma origem nao equivale a um `required_file`. O mesmo SAP pode fornecer varios
arquivos distintos, diferenciados por periodo, estado ou contexto:

```text
ZSD008 mes 7       -> zsd008_mes_7
ZSD008 mes 8       -> zsd008_mes_8
FBL5N aberta       -> fbl5n_aberta
FBL5N compensada   -> fbl5n_compensada
```

A hierarquia de inferencia e:

1. detectar entidades de arquivo;
2. identificar atributos diferenciadores, como mes, estado ou safra;
3. classificar a origem de cada entidade;
4. classificar dominio e pattern;
5. gerar um item separado em `required_files` para cada entidade.

Nunca colapsar dois arquivos em um unico input apenas porque ambos vieram do
mesmo sistema. Termos como `mes 7`, `mes 8`, `atual`, `anterior`, `aberta`,
`compensada`, `origem A`, `origem B`, `safra 2024` e `safra 2025` devem ser
preservados no identificador do arquivo quando diferenciarem entidades.

## SAP

**Descricao:** sistema de origem de relatorios financeiros, contabeis, comerciais e de faturamento.

**Origem:** SAP ERP e exportacoes de transacoes ou relatorios SAP.

**Extensoes mais comuns:** `xlsx` como padrao preferencial; `csv` somente quando confirmado no arquivo real.

**Colunas normalmente encontradas:** `Documento`, `Nº documento`, `N° documento`, `Conta`, `CNPJ`, `Data`, `Montante`, `Montante em moeda interna`, `Valor`, `Centro de custo`.

**Categoria:** `financeiro`, podendo ser `faturamento` quando o processo for especificamente de faturamento.

**Tipos de automacao compativeis:** conciliacao, validacao, consolidacao, saneamento e preparacao de datasets.

**Outputs comuns:** `conciliacao.xlsx`, `divergencias.xlsx`, `resultado_sap.xlsx`, `dataset.csv`.

**Regra:** ao detectar relatorio SAP, nao gerar `accepted_extensions: [csv]` por inferencia generica.

## FS10N

**Descricao:** relatorio SAP de partidas ou movimentos financeiros usado em conciliacoes e analises contabeis.

**Origem:** SAP, transacao/relatorio FS10N.

**Extensoes mais comuns:** `xlsx`.

**Colunas normalmente encontradas:** `Conta`, `Data`, `Documento`, `Texto`, `Montante`, `Montante em moeda interna`, `Empresa`.

**Categoria:** `financeiro`.

**Tipos de automacao compativeis:** conciliacao com Billing, Prefeitura ou outras bases; validacao e consolidacao.

**Outputs comuns:** `conciliacao.xlsx`, `divergencias.xlsx`, `resultado_sap.xlsx`.

## FBL3N

**Descricao:** relatorio SAP de itens de contas contabeis ou razao geral.

**Origem:** SAP, transacao/relatorio FBL3N.

**Extensoes mais comuns:** `xlsx`.

**Colunas normalmente encontradas:** `Conta`, `Empresa`, `Data do documento`, `Data de lancamento`, `Documento`, `Referencia`, `Montante`, `Texto`.

**Categoria:** `financeiro`.

**Tipos de automacao compativeis:** conciliacao contabil, validacao de saldos, consolidacao e deteccao de divergencias.

**Outputs comuns:** `conciliacao.xlsx`, `divergencias.xlsx`, `resultado_sap.xlsx`.

## FBL5N Aberta

**Descricao:** relatorio SAP de itens em aberto de contas a receber por cliente.

**Origem:** SAP, relatorio FBL5N com filtro de partidas abertas.

**Extensoes mais comuns:** `xlsx`.

**Colunas normalmente encontradas:** `Cliente`, `Nome do cliente`, `Empresa`, `Documento`, `Vencimento`, `Montante`, `Referencia`, `Data de lancamento`.

**Categoria:** `financeiro`.

**Tipos de automacao compativeis:** aging, cobranca, conciliacao de recebiveis, validacao de vencimentos e cruzamento com Billing.

**Outputs comuns:** `conciliacao.xlsx`, `divergencias.xlsx`, `contas_receber_abertas.xlsx`.

## FBL5N Compensada

**Descricao:** relatorio SAP de itens compensados de contas a receber por cliente.

**Origem:** SAP, relatorio FBL5N com filtro de partidas compensadas.

**Extensoes mais comuns:** `xlsx`.

**Colunas normalmente encontradas:** `Cliente`, `Empresa`, `Documento`, `Documento de compensacao`, `Data de compensacao`, `Montante`, `Referencia`.

**Categoria:** `financeiro`.

**Tipos de automacao compativeis:** conciliacao de recebimentos, auditoria de compensacoes, validacao e cruzamento com Billing ou Prefeitura.

**Outputs comuns:** `conciliacao.xlsx`, `divergencias.xlsx`, `compensacoes.xlsx`.

## ZSD008

**Descricao:** relatorio SAP comercial ou de faturamento usado para cruzar notas, pedidos, documentos e valores.

**Origem:** SAP, transacao/relatorio ZSD008.

**Extensoes mais comuns:** `xlsx`.

**Colunas normalmente encontradas:** `Nº Nota Fiscal`, `N° RPS`, `Fatura Billing`, `Cliente`, `CNPJ`, `Valor Bruto`, `Data`, `Material`.

**Categoria:** `financeiro` ou `faturamento` quando o contexto for explicitamente de faturamento.

**Tipos de automacao compativeis:** conciliacao com Billing ou Prefeitura, validacao fiscal e geracao de relatorios.

**Outputs comuns:** `conciliacao.xlsx`, `divergencias.xlsx`, `resultado_faturamento.xlsx`.

## Billing

**Descricao:** base de cobranca ou faturamento de uma aplicacao financeira/comercial, tratada como fonte distinta do SAP.

**Origem:** sistema de Billing, exportacao financeira ou plataforma comercial.

**Extensoes mais comuns:** `xlsx` ou `csv`, conforme a exportacao real.

**Colunas normalmente encontradas:** `Fatura Billing`, `Documento`, `Cliente`, `CNPJ`, `Data`, `Valor`, `Valor Bruto`, `Status`.

**Categoria:** `financeiro`.

**Tipos de automacao compativeis:** conciliacao com SAP, Prefeitura ou contas a receber; validacao e consolidacao.

**Outputs comuns:** `conciliacao.xlsx`, `divergencias.xlsx`, `billing_tratado.xlsx`.

**Regra:** Billing nao deve ser renomeado para SAP nem inferido como Faturamento sem evidencia textual adicional.

## Prefeitura

**Descricao:** exportacao municipal de notas fiscais, RPS ou servicos prestados.

**Origem:** portal ou sistema da Prefeitura.

**Extensoes mais comuns:** `csv`; `xlsx` quando confirmado pela exportacao.

**Colunas normalmente encontradas:** `Numero NF`, `Numero RPS`, `CNPJ`, `Valor Servico`, `Valor Serviço`, `Data`, `Prestador`, `Tomador`.

**Categoria:** `faturamento` ou `fiscal`.

**Tipos de automacao compativeis:** conciliacao com SAP/Billing, validacao fiscal e saneamento.

**Outputs comuns:** `conciliacao.xlsx`, `divergencias.xlsx`, `notas_validadas.xlsx`.

**Regra:** Prefeitura nao e SAP. Quando ambos aparecem, modele dois inputs separados.

## Antifraude

**Descricao:** tratamento, saneamento, classificacao ou score de risco sobre transacoes ou cadastros.

**Origem:** base operacional, pagamentos, clientes ou transacoes.

**Extensoes mais comuns:** `xlsx` ou `csv`.

**Colunas normalmente encontradas:** `ID`, `Child`, `MID`, `Product Description`, `Total Amount Due`, `Cliente`, `Valor`, `Data`, `Status`.

**Categoria:** `risco`.

**Tipos de automacao compativeis:** validacao, classificacao, saneamento e priorizacao de analise.

**Outputs comuns:** `antifraude.xlsx`, `antifraude_vf.xlsx`, `casos_suspeitos.xlsx`.

## Power BI

**Descricao:** preparacao de dataset para relatorios, dashboards e modelos analiticos.

**Origem:** bases operacionais, financeiras, comerciais ou exportacoes de sistemas.

**Extensoes mais comuns:** `csv` ou `xlsx` na entrada; `csv` como output padrao.

**Colunas normalmente encontradas:** `ID`, `Data`, `Categoria`, `Valor`, `Status`, `Cliente`, `Centro de custo`.

**Categoria:** `power_bi`.

**Tipos de automacao compativeis:** validacao, limpeza, normalizacao, consolidacao e exportacao de dataset.

**Outputs comuns:** `dataset.csv`, `dataset_power_bi.xlsx`.

## Regras para o manifesto

Ao identificar FS10N, FBL3N, FBL5N ou ZSD008, gerar no minimo:

```yaml
category: financeiro
required_files:
  - id: fs10n
    display_name: FS10N
    accepted_extensions:
      - xlsx
```

Complete `required_columns` somente com colunas observadas ou confirmadas. Nao invente chaves de conciliacao.

Ao identificar FS10N e Billing no mesmo prompt, use dois itens em `required_files`, com `id: fs10n` e `id: billing`. Ao identificar FS10N e Prefeitura, mantenha `id: fs10n` e `id: prefeitura_nfse` separados.

## Resultado esperado

Estas regras permitem que o Automation Designer produza manifestos aderentes ao dominio descrito, reduza o uso de `entrada`, `automacao` e `resultado.xlsx` e preserve o fallback generico apenas quando o prompt nao oferecer contexto suficiente.
