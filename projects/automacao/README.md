# Automacao Gerada

## Objetivo

Recebo diariamente um relatório FS10N exportado do SAP e um relatório de Billing. Preciso conciliar os documentos e gerar um Excel contendo conciliados, divergentes, apenas SAP e apenas Billing.

## Inputs

- `faturamento`: Faturamento (xlsx)
- `sap`: SAP (xlsx)

## Outputs

- `resultado.xlsx`

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
