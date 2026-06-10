"""Controle de estoque persistente (o "banco" do sistema).

O estoque e um arquivo JSON simples em `data/estoque.json` que mapeia o
EAN-13 de cada produto para o nome e a quantidade disponivel. Os dois
processos usam o MESMO banco:

  - Recebimento  -> CREDITA (entrada de mercadoria que chegou fisicamente).
  - Caixa        -> DEBITA  (baixa a cada venda).

Estrutura do arquivo:
  {
    "7890000000017": {"nome": "Cafe Pilao 500g", "quantidade": 3},
    "7890000000024": {"nome": "Leite Itambe 1L", "quantidade": 2},
    ...
  }

Chaveamos por EAN-13 (o codigo de venda) porque o caixa identifica o
produto por EAN. O recebimento, que le RFID, converte RFID -> EAN-13 pelo
catalogo antes de creditar.
"""

from pathlib import Path
import json

ESTOQUE_PATH = Path(__file__).parent.parent / "data" / "estoque.json"


def carregar(path=ESTOQUE_PATH):
    """Retorna o estoque como dict {ean13: {"nome", "quantidade"}}.

    Se o arquivo ainda nao existir, retorna um dict vazio — ou seja, um
    estoque zerado (situacao inicial, antes de qualquer recebimento).
    """
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar(estoque, path=ESTOQUE_PATH):
    """Grava o estoque em JSON (cria o diretorio pai se necessario).

    Sempre utf-8 explicito e com newline final (convencao POSIX).
    Retorna o Path do arquivo escrito.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(estoque, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return p


def quantidade(estoque, ean13):
    """Quantidade atual em estoque do produto (0 se nao houver entrada)."""
    item = estoque.get(ean13)
    return item["quantidade"] if item else 0


def creditar(estoque, ean13, nome, qtd):
    """Adiciona `qtd` unidades ao estoque do produto (entrada de mercadoria).

    Se o produto ainda nao existe no banco, cria a entrada. Retorna a
    quantidade resultante.
    """
    if ean13 in estoque:
        estoque[ean13]["quantidade"] += qtd
        estoque[ean13]["nome"] = nome  # mantem o nome mais recente conhecido
    else:
        estoque[ean13] = {"nome": nome, "quantidade": qtd}
    return estoque[ean13]["quantidade"]


def debitar(estoque, ean13, qtd=1):
    """Remove `qtd` unidades do estoque (venda no caixa).

    Retorna True se havia saldo suficiente (e efetua a baixa); retorna
    False caso contrario, SEM alterar o estoque (nao deixa quantidade
    negativa).
    """
    atual = quantidade(estoque, ean13)
    if atual < qtd:
        return False
    estoque[ean13]["quantidade"] = atual - qtd
    return True
