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
├── recebimento.py    Processo 1: concilia RFID com NF e abastece o estoque
├── caixa.py          Processo 2: caixa (produtos e boletos) com baixa de estoque
├── rfid_mock.py      Mock HTTP do leitor RFID (substitui o rfid.exe)
├── sistema.py        Nucleo do dominio (catalogo, estoque, detector,
│                     febraban, leitor RFID e formatacao das saidas)
└── data/
    ├── catalog.json  Catalogo de produtos cadastrados
    ├── estoque.json  Banco de estoque (gerado em runtime; nao versionado)
    └── nf/           Notas fiscais de teste (3 cenarios)
```

> O relatorio de recebimento e o cupom do caixa sao impressos no **terminal**
> (nao sao gravados em arquivo). O unico estado persistido em runtime e o
> estoque (`data/estoque.json`).

---

## Como rodar

> **Windows:** use `python` e barras invertidas (`data\nf\...`).
> **macOS/Linux:** use `python3` e barras normais (`data/nf/...`).
>
> Os exemplos abaixo usam o formato Windows.

### Processo 1 - Recebimento

Precisa de **duas janelas** do terminal abertas simultaneamente.

**Janela 1** - iniciar o mock do leitor RFID:

```
python rfid_mock.py
```

Servidor sobe em `http://127.0.0.1:3000/tags` e deve ficar rodando.

**Janela 2** - rodar a conciliacao contra uma NF:

```
python recebimento.py --nf data\nf\nf_001_normal.json
```

O programa faz multiplas leituras do mock ate o inventario convergir
(algoritmo de max-merge), compara com a NF e **imprime o relatorio no
terminal**. Alem disso, **credita o que chegou fisicamente no estoque**
(`data\estoque.json`) - esse e o banco que o caixa consome.

> Use `--reset-estoque` para zerar o estoque antes de creditar (util em
> demos, evita acumular o mesmo recebimento varias vezes).

### Processo 2 - Caixa

Nao precisa do mock RFID, mas **consome o estoque** abastecido pelo
recebimento: a cada venda da **baixa** no `data\estoque.json`. Um produto
sem saldo nao e vendido (mensagem `SEM ESTOQUE`). Por isso, rode o
recebimento ao menos uma vez antes do caixa.

**Modo interativo** (digite codigos um por linha, encerre com `FIM`):

```
python caixa.py
```

**Modo arquivo** (le codigos de um `.txt`):

```
python caixa.py --arquivo compra_teste.txt
```

O cupom e impresso na tela e a baixa do estoque e persistida em
`data\estoque.json`.

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

## Atalhos (opcional)

Para simplificar o uso manual, ha atalhos de terminal. Carregue uma vez por
sessao e use comandos curtos (`rfid.exe`, `recebimento`, `caixa`, etc.):

- **macOS/Linux (zsh/bash) e Git Bash:** `source aliases.sh`
- **Windows (PowerShell):** `. .\aliases.ps1`

Depois rode `ajuda` para ver todos os comandos disponiveis.

---

## Documentacao adicional

- `docs/MANUAL_DE_APOIO.txt` - guia passo a passo para colegas do grupo
  testarem localmente em Windows, sem assumir conhecimento tecnico.
- `docs/descricao-trabalho-final.pdf` - especificacao original do trabalho.
- `docs/sobre-emulador-rfid.pdf` - notas sobre o emulador RFID de referencia.
