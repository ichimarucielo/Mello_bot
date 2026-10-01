# Comparacao ZSD008 entre Periodos

## Objetivo

Recebo diariamente dois documentos:
zsd008 SAP faturamento da stelo xslx
prefeitura csv
Preciso que todas as nfs estejam presentes na prefeitura, as que não tiverem tem que ser dadas como divergencia em um nova pagina.
Ou seja, 2 paginas:
1 - Divergentes, não conciliadas
2 - Conciliadas, geral
a referencia é a prefeitura.

## Inputs

- `zsd008`: ZSD008 (xlsx)
- `prefeitura_nfse`: Prefeitura NFS-e (csv)

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
