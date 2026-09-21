# Conciliacao Contas a Pagar x Contas a Receber

## Objetivo

Crie um relatório chamado: "Diferença de pagar e receber"
Relatorios usados serão 2: zsd008 em formato de excel do mes 07 (julho) e outro sera o zsd008 em formato de excel do mes 08 (agosto)
Preciso que diferencie notas fiscais compensadas e em abertas por meio de status.
Gere um relatório chamado diferença receber x a pagar.

## Inputs

- `zsd008_mes_07`: ZSD008 Mes 07 (xlsx)
- `zsd008_mes_08`: ZSD008 Mes 08 (xlsx)

## Outputs

- `conciliacao.xlsx`
- `divergencias.xlsx`

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
