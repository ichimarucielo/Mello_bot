# ComparaçãoFBL5N

## Objetivo

Recebi dois relatórios financeiros.

O primeiro representa o razão contábil completo contendo faturamentos, compensações, baixas, aging, vencimentos e histórico dos documentos.

O segundo representa os recebimentos realizados.

Preciso construir uma análise de conciliação entre os dois arquivos.

Objetivos:

- identificar quais documentos do relatório contábil já possuem recebimento;
- identificar quais documentos permanecem sem recebimento;
- identificar divergências de valor entre faturamento e recebimento;
- identificar documentos duplicados;
- consolidar valores por cliente;
- consolidar valores por mês;
- gerar indicadores de recebimento;
- calcular percentual conciliado e não conciliado;
- destacar os maiores impactos financeiros;
- criar um diagnóstico apontando possíveis problemas de qualidade dos dados.

A solução deve:

- identificar automaticamente a melhor chave de conciliação;
- preservar zeros à esquerda;
- tratar as chaves como texto;
- remover espaços extras;
- consolidar duplicidades quando necessário;
- sugerir regras de agregação quando houver múltiplos registros para o mesmo documento.

Quero receber primeiro o Execution Plan contendo:

- documentos identificados;
- chaves sugeridas;
- operações propostas;
- riscos encontrados;
- outputs sugeridos.

Não gere o projeto ainda.

Aguarde aprovação após apresentar o plano.

## Inputs

- `fbl5n_aberta`: FBL5N Em Aberto (xlsx)
- `fbl5n_compensada`: FBL5N Compensada (xlsx)

## Outputs

- `fbl5nConciliação.xlsx`

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
