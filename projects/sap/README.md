# Automacao Sap

## Objetivo

eu recebo duas bases. A primeira base é um xlsx do mes 7 zsd008 sap, a outra é um xlsx do mes 8 zsd008 sap. Preciso cruzar ambas e ter dados limpos e tratados para que eu descubra o que ainda está aberto, fazendo compensadas - abertas. Eu espero um relatorio de saída apenas, em xlsx para "diferença em aberto".

## Inputs

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

## Proximos passos de implementacao

- confirmar as colunas e chaves de negocio com os arquivos reais;
- substituir os TODOs pela regra especifica do ETL;
- revisar os nomes e a pasta dos outputs declarados no manifesto;
- adicionar testes com casos validos, divergentes e arquivos vazios;
- executar uma validacao end-to-end antes de publicar a automacao.
