# Trabalho final da disciplina de **Automacao Industrial**.

Simulador de dois processos comuns de um mercado, automatizados por leitores
de codigo:

- **Recebimento de mercadoria** - leitor RFID concilia o estoque que chegou
  contra a Nota Fiscal (NF) enviada pelo fornecedor.
- **Caixa** - leitor de codigo de barras processa produtos (EAN-13) e
  boletos (FEBRABAN), emitindo cupom fiscal ao final.

Todo o sistema roda local, sem hardware fisico: o leitor RFID e simulado por
um mock HTTP que reproduz o comportamento do `rfid.exe` original (falhas
Bernoulli por tag, ordem aleatoria), e os codigos de barras de produtos e
boletos sao digitados/colados no terminal.

---

## Requisitos

- Python **3.9 ou superior**
- Nenhuma dependencia externa - o projeto usa **apenas a biblioteca padrao**
  do Python. Nao e preciso rodar `pip install`.

---

## Estrutura do projeto

```
automacao-industrial/
├── bin/                  Entry-points executaveis
│   ├── recebimento.py    Processo 1: concilia RFID com NF
│   └── caixa.py          Processo 2: caixa (produtos e boletos)
├── src/                  Modulos do dominio
│   ├── rfid_client.py    Cliente HTTP do leitor + algoritmo de convergencia
│   ├── catalog.py        Catalogo de produtos (EAN-13 -> nome/preco)
│   ├── estoque.py        Banco de estoque (credita no recebimento, debita no caixa)
│   ├── febraban.py       Parser de boleto (codigo de barras / linha digitavel)
│   ├── detector.py       Detecta se um codigo lido e produto ou boleto
│   └── relatorios.py     Geradores de relatorio de recebimento e cupom fiscal
├── mock-server/
│   └── rfid_mock.py      Mock HTTP do leitor RFID (substitui o rfid.exe)
├── data/
│   ├── catalog.json      Catalogo de produtos cadastrados
│   ├── estoque.json      Banco de estoque (gerado em runtime; nao versionado)
│   └── nf/               Notas fiscais de teste (3 cenarios)
├── tests/                Testes unitarios (unittest)
└── output/               Saidas geradas em runtime
    ├── relatorios/       Relatorios de recebimento
    └── cupons/           Cupons fiscais do caixa
```

---

## Como rodar

> **Windows:** use `python` e barras invertidas (`bin\recebimento.py`).
> **macOS/Linux:** use `python3` e barras normais (`bin/recebimento.py`).
>
> Os exemplos abaixo usam o formato Windows.

### Processo 1 - Recebimento

Precisa de **duas janelas** do terminal abertas simultaneamente.

**Janela 1** - iniciar o mock do leitor RFID:

```
python mock-server\rfid_mock.py
```

Servidor sobe em `http://127.0.0.1:3000/tags` e deve ficar rodando.

**Janela 2** - rodar a conciliacao contra uma NF:

```
python bin\recebimento.py --nf data\nf\nf_001_normal.json
```

O programa faz multiplas leituras do mock ate o estoque convergir
(algoritmo de max-merge), compara com a NF e gera o relatorio em
`output\relatorios\`. Alem disso, **credita o que chegou fisicamente no
estoque** (`data\estoque.json`) - esse e o banco que o caixa consome.

> Use `--reset-estoque` para zerar o estoque antes de creditar (util em
> demos, evita acumular o mesmo recebimento varias vezes).

### Processo 2 - Caixa

Nao precisa do mock RFID, mas **consome o estoque** abastecido pelo
recebimento: a cada venda da **baixa** no `data\estoque.json`. Um produto
sem saldo nao e vendido (mensagem `SEM ESTOQUE`). Por isso, rode o
recebimento ao menos uma vez antes do caixa.

**Modo interativo** (digite codigos um por linha, encerre com `FIM`):

```
python bin\caixa.py
```

**Modo arquivo** (le codigos de um `.txt`):

```
python bin\caixa.py --arquivo compra_teste.txt
```

O cupom e impresso na tela e salvo em `output\cupons\`, e a baixa do
estoque e persistida em `data\estoque.json`.

---

## Cenarios de teste prontos

| Arquivo                       | Cenario               | Resultado esperado                  |
|-------------------------------|-----------------------|-------------------------------------|
| `data/nf/nf_001_normal.json`  | NF bate com o leitor  | `STATUS: OK`                        |
| `data/nf/nf_002_com_falta.json` | NF lista itens nao recebidos | `STATUS: DIVERGENCIA - 2 faltando` |
| `data/nf/nf_003_com_sobra.json` | Chegou mais do que a NF previa | `STATUS: DIVERGENCIA - X em sobra` |

Para o caixa, exemplos de codigos EAN-13 validos estao no catalogo
(`data/catalog.json`): cafe (`7890000000017`), leite (`7890000000024`),
arroz (`7890000000031`), etc. O sistema tambem aceita codigos "sujos"
com tracos, pontos ou espacos (sao limpos automaticamente).

---

## Testes

Suite com `unittest` (biblioteca padrao):

```
python -m unittest discover tests
```

Cobertura inclui: cliente RFID e algoritmo de convergencia, parser FEBRABAN
(barra e linha digitavel, validacao de DV), catalogo de produtos e detector
de tipo de codigo.

### Log detalhado (recomendado para o grupo)

Para um log didatico no terminal - mostra, teste a teste, o que esta sendo
verificado, o resultado (PASSOU/FALHOU) e, em caso de falha, o motivo
completo - use o runner `run_tests.py`:

```
python run_tests.py            # log completo, teste a teste
python run_tests.py --quieto   # so o resumo final
```

> No macOS/Linux use `python3` no lugar de `python`.

Tambem usa apenas a biblioteca padrao (nao precisa instalar nada). As cores
desligam sozinhas quando a saida nao e um terminal; para forcar sem cores,
rode com `NO_COLOR=1 python run_tests.py`.

---

## Documentacao adicional

- `docs/MANUAL_DE_APOIO.txt` - guia passo a passo para colegas do grupo
  testarem localmente em Windows, sem assumir conhecimento tecnico.
- `docs/descricao-trabalho-final.pdf` - especificacao original do trabalho.
- `docs/sobre-emulador-rfid.pdf` - notas sobre o emulador RFID de referencia.
