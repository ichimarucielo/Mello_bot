# Comparacao ZSD008 entre Periodos

## Objetivo

Recebi dois relatórios ZSD008 do SAP.

Cada relatório representa o faturamento de um período diferente.

Objetivo:

Identificar quais Notas Fiscais deixaram de ser faturadas entre os períodos.

Considere que uma mesma Nota Fiscal pode aparecer mais de uma vez devido à existência de diferentes produtos ou serviços.

Regras de negócio:

1. Utilizar como chave principal de comparação:

- Número da Nota Fiscal

2. Caso existam duplicidades de NF dentro do mesmo relatório:

- Consolidar por Nota Fiscal
- Somar valores faturados
- Somar quantidades quando aplicável
- Agrupar produtos em lista

3. Produzir os seguintes outputs:

### 1. Resumo Executivo

- Quantidade de NFs no relatório antigo
- Quantidade de NFs no relatório novo
- Quantidade de NFs presentes em ambos
- Quantidade de NFs que deixaram de ser faturadas
- Quantidade de NFs novas

### 2. NFs Perdidas

Retornar todas as NFs que existiam no relatório antigo e não existem no relatório novo.

Para cada NF retornar:

- NF
- Cliente
- CNPJ
- Data de emissão
- Valor faturado
- Produtos
- Mês/Ano

### 3. NFs Novas

Retornar NFs que aparecem no relatório novo mas não estavam no antigo.

### 4. Análise por Cliente

Agrupar por cliente e retornar:

- Quantidade de NFs perdidas
- Valor perdido
- Quantidade de NFs novas
- Valor novo
- Saldo líquido

Ordenar por maior impacto financeiro.

### 5. Análise Mensal

Criar visão mês a mês contendo:

- Mês
- Quantidade de NFs faturadas
- Valor faturado
- Variação percentual de quantidade
- Variação percentual de valor

### 6. Top Perdas

Top 20 clientes com maior redução de faturamento.

### 7. Diagnóstico

Explicar:

- Quais clientes deixaram de faturar
- Quais clientes reduziram faturamento
- Quais clientes aumentaram faturamento
- Possíveis riscos identificados

Regras técnicas:

- Tratar campos monetários corretamente
- Ignorar diferenças de formatação
- Ignorar espaços extras
- Tratar NF como texto para evitar perda de zeros à esquerda
- Não utilizar aproximações
- Mostrar os números exatos

No final gerar uma classificação:

🟢 Sem perda relevante
🟡 Atenção
🔴 Perda significativa

com justificativa baseada nos valores encontrados.

## Inputs

- `zsd008_antigo`: ZSD008 Antigo (xlsx)
- `zsd008_novo`: ZSD008 Novo (xlsx)

## Outputs

- `comparação_mes_zsd008.xlsx`

## Como executar

```bash
python src/main.py --help
```

Preencha os argumentos definidos no manifesto e execute o comando a partir da raiz deste projeto.

## Estrutura

```text
src/main.py
data/input/
data/output/
manifest.yaml
```

## Criterios de aceite

- os inputs devem ser validados conforme as colunas declaradas;
- a regra de negocio deve ser implementada no entrypoint;
- todos os outputs declarados devem ser gerados na pasta configurada;
- a execucao deve retornar codigo zero em caso de sucesso;
- o resultado deve ser revisado com dados reais antes de producao.

## Proximos passos de implementacao

- confirmar as colunas e chaves de negocio com os arquivos reais;
- substituir os TODOs pela regra especifica do ETL;
- revisar os nomes e a pasta dos outputs declarados no manifesto;
- adicionar testes com casos validos, divergentes e arquivos vazios;
- executar uma validacao end-to-end antes de publicar a automacao.
