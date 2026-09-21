# Report Patterns

## Objetivo

Ensinar o MELLO AI a reconhecer relatórios reais utilizados nas automações do MELLO BOT.

O objetivo não é apenas identificar a origem do sistema, mas compreender:

- tipo do relatório;
- formato esperado;
- colunas conhecidas;
- chaves de negócio;
- uso comum;
- padrões de automação relacionados.

Quando não houver evidência suficiente, o MELLO AI deve declarar hipótese e solicitar validação.

Nunca inventar colunas.

---

# SAP

## Regra Geral

Quando identificar relatórios SAP:

- assumir formato preferencial XLSX;
- não assumir CSV;
- categoria financeira;
- não colapsar múltiplos arquivos SAP em um único input.

Relatórios SAP diferentes devem gerar inputs distintos.

Exemplo:

"FS10N atual e FS10N anterior"

↓

required_files:

- fs10n_atual

- fs10n_anterior

---

# FS10N

Origem:

SAP

Formato comum:

xlsx

Uso comum:

- contas contábeis
- saldos
- conciliação financeira

Possíveis padrões:

- conciliação
- comparação
- fechamento

Chaves frequentes:

- Nº documento
- Conta
- Montante em moeda interna

---

# FBL3N

Origem:

SAP

Formato comum:

xlsx

Uso comum:

- partidas de razão
- análise contábil

Chaves frequentes:

- Documento
- Conta
- Valor

---

# FBL5N Aberta

Origem:

SAP

Formato comum:

xlsx

Uso comum:

- contas a receber abertas

Quando identificar:

FBL5N Aberta

gerar:

required_files:

- fbl5n_aberta

Nunca:

- sap

---

# FBL5N Compensada

Origem:

SAP

Formato comum:

xlsx

Uso comum:

- contas a receber compensadas

Quando identificar:

FBL5N Compensada

gerar:

required_files:

- fbl5n_compensada

Nunca:

- sap

---

# ZSD008

Origem:

SAP

Formato comum:

xlsx

Objetivo comum:

- faturamento
- billing
- prefeitura
- notas fiscais

Colunas frequentemente observadas:

- Razão Social
- CNPJ
- Descrição
- Nº Nota Fiscal
- N° RPS
- Fatura Billing
- Data RPS
- Valor Bruto
- Período

Chave mais comum:

- Nº Nota Fiscal

Valor mais comum:

- Valor Bruto

Quando identificar:

ZSD008 mês 07
ZSD008 mês 08

gerar:

required_files:

- zsd008_mes_07

- zsd008_mes_08

Nunca:

required_files:

- sap

---

# Billing

Origem:

Billing

Formato comum:

xlsx

Billing não é SAP.

Billing não é faturamento.

Billing deve ser tratado como fonte própria.

Quando identificar:

Billing

gerar:

required_files:

- billing

---

# Prefeitura

Origem:

Prefeitura

Formato comum:

csv

Encoding frequente:

latin1

Separador frequente:

;

Prefeitura não deve ser confundida com SAP.

Quando existir:

SAP + Prefeitura

gerar dois inputs.

---

# Antifraude

Origem:

Operacional

Formato comum:

xlsx

Uso comum:

- classificação
- score
- prevenção de fraude

Output comum:

antifraude.xlsx

---

# Power BI

Objetivo:

Preparação de datasets

Outputs comuns:

- dataset.csv
- dataset.xlsx

---

# Regra de Ouro

Primeiro responder:

"Quantos arquivos o usuário descreveu?"

Depois responder:

"Qual a origem desses arquivos?"

Nunca agrupar múltiplos arquivos somente porque pertencem ao mesmo sistema.

