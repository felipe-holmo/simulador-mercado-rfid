"""Nucleo do simulador de mercado.

Reune, num unico modulo, tudo que os dois processos precisam:

  - Catalogo de produtos (carga + indices de lookup O(1)).
  - Estoque persistente (o "banco": credita no recebimento, debita no caixa).
  - Deteccao do tipo de codigo lido no caixa (produto / boleto / FIM).
  - Parse e validacao de boletos FEBRABAN (44 e 47 digitos).
  - Cliente do leitor RFID + algoritmo de convergencia (max-merge).
  - Formatacao (em texto) do relatorio de recebimento e do cupom fiscal.

Usa apenas a biblioteca padrao.
"""

import json
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

# Raiz do projeto (este arquivo vive na raiz, ao lado da pasta data/).
REPO_ROOT = Path(__file__).parent
CATALOG_PATH = REPO_ROOT / "data" / "catalog.json"
ESTOQUE_PATH = REPO_ROOT / "data" / "estoque.json"


# ===========================================================================
# Catalogo de produtos
# ===========================================================================

def carregar_catalogo(path=CATALOG_PATH):
    """Retorna a lista de produtos lida do JSON do catalogo."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def indices(catalogo):
    """Retorna (por_rfid, por_ean): dois dicts para lookup O(1).

    A ordem (por_rfid, por_ean) e contratual: o caixa desempacota nesta
    ordem. O recebimento usa por_rfid (le RFID); o caixa usa por_ean.
    """
    por_rfid = {produto["rfid"]: produto for produto in catalogo}
    por_ean = {produto["ean13"]: produto for produto in catalogo}
    return por_rfid, por_ean


# ===========================================================================
# Estoque (banco persistente em data/estoque.json)
# ===========================================================================

def estoque_carregar(path=ESTOQUE_PATH):
    """Retorna o estoque {ean13: {"nome", "quantidade"}}.

    Se o arquivo ainda nao existir, retorna dict vazio (estoque zerado).
    """
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def estoque_salvar(estoque, path=ESTOQUE_PATH):
    """Grava o estoque em JSON (cria o diretorio pai). Retorna o Path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(estoque, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return p


def estoque_quantidade(estoque, ean13):
    """Quantidade atual em estoque do produto (0 se nao houver entrada)."""
    item = estoque.get(ean13)
    return item["quantidade"] if item else 0


def estoque_creditar(estoque, ean13, nome, qtd):
    """Adiciona `qtd` unidades ao estoque (entrada). Retorna o saldo final."""
    if ean13 in estoque:
        estoque[ean13]["quantidade"] += qtd
        estoque[ean13]["nome"] = nome  # mantem o nome mais recente conhecido
    else:
        estoque[ean13] = {"nome": nome, "quantidade": qtd}
    return estoque[ean13]["quantidade"]


def estoque_debitar(estoque, ean13, qtd=1):
    """Remove `qtd` unidades (venda). True se havia saldo; False caso
    contrario (sem deixar quantidade negativa)."""
    atual = estoque_quantidade(estoque, ean13)
    if atual < qtd:
        return False
    estoque[ean13]["quantidade"] = atual - qtd
    return True


# ===========================================================================
# Deteccao do tipo de codigo (caixa)
# ===========================================================================

def detectar(codigo):
    """Classifica o codigo lido pelo tamanho.

    Retorna: "produto" (13), "boleto_barra" (44), "boleto_linha" (47),
    "finalizar" (codigo == FIM) ou "invalido".
    """
    if codigo.upper() == "FIM":
        return "finalizar"
    if codigo.isdigit():
        if len(codigo) == 13:
            return "produto"
        if len(codigo) == 44:
            return "boleto_barra"
        if len(codigo) == 47:
            return "boleto_linha"
    return "invalido"


# ===========================================================================
# Boleto FEBRABAN
# ===========================================================================

def _calcular_dv_mod10(digitos):
    """DV Mod 10 (FEBRABAN): pesos 2,1,2,1...; algarismos somados se >9."""
    soma = 0
    peso = 2
    for caractere in reversed(digitos):
        produto = int(caractere) * peso
        if produto > 9:
            produto = (produto // 10) + (produto % 10)
        soma += produto
        peso = 1 if peso == 2 else 2
    return (10 - (soma % 10)) % 10


def validar_dv_mod10(linha_digitavel):
    """Valida o DV dos 3 campos da linha digitavel (47 digitos)."""
    if len(linha_digitavel) != 47 or not linha_digitavel.isdigit():
        return False
    campos = (
        (linha_digitavel[0:9], linha_digitavel[9]),
        (linha_digitavel[10:20], linha_digitavel[20]),
        (linha_digitavel[21:31], linha_digitavel[31]),
    )
    for dados, dv in campos:
        if _calcular_dv_mod10(dados) != int(dv):
            return False
    return True


def extrair_valor(codigo):
    """Valor do boleto em reais. 44 dig: codigo[9:19]; 47 dig: codigo[37:47]."""
    if len(codigo) == 44:
        centavos = int(codigo[9:19])
    elif len(codigo) == 47:
        centavos = int(codigo[37:47])
    else:
        raise ValueError(f"Tamanho invalido para extrair valor: {len(codigo)}")
    return centavos / 100


def parse_boleto(codigo):
    """Parse de boleto FEBRABAN (44 ou 47 digitos).

    Valida DV Mod 10 na linha de 47; aceita 44 por tamanho. Retorna
    {"tipo","banco","valor","codigo_original"} ou levanta ValueError.
    """
    if not isinstance(codigo, str) or not codigo.isdigit():
        raise ValueError("Codigo deve conter apenas digitos")
    if len(codigo) not in (44, 47):
        raise ValueError(f"Tamanho invalido: esperado 44 ou 47, recebido {len(codigo)}")
    if len(codigo) == 47 and not validar_dv_mod10(codigo):
        raise ValueError("DV Mod 10 invalido na linha digitavel")
    return {
        "tipo": "boleto",
        "banco": codigo[:3],
        "valor": extrair_valor(codigo),
        "codigo_original": codigo,
    }


# ===========================================================================
# Leitor RFID (cliente HTTP) + convergencia adaptativa
# ===========================================================================

DEFAULT_RFID_URL = "http://127.0.0.1:3000"

# Teto absoluto de leituras: evita loop infinito se o leitor nunca convergir.
MAX_LEITURAS = 20


class RFIDClient:
    def __init__(self, base_url=DEFAULT_RFID_URL):
        self.base_url = base_url

    def ler_tags(self):
        """GET /tags. Retorna a lista de tags lidas (pode ter duplicatas)."""
        url = self.base_url.rstrip("/") + "/tags"
        with urllib.request.urlopen(url) as resposta:
            corpo = resposta.read().decode("utf-8")
        return json.loads(corpo)["tags"]


def reconciliar(client, min_leituras=3, paciencia=2, verbose=True):
    """Le tags repetidamente ate convergir e retorna (inventario, num_leituras).

    O inventario e um Counter: por codigo, mantemos o MAXIMO ja observado
    entre as leituras (max-merge), o melhor estimador da quantidade fisica
    real diante de falhas de leitura. Para quando ja houve >= min_leituras
    E as ultimas `paciencia` leituras nao trouxeram nada novo. Tem teto
    MAX_LEITURAS para nunca rodar infinito.
    """
    inventario = Counter()
    num_leituras = 0
    leituras_sem_novidade = 0

    while True:
        tags = client.ler_tags()
        num_leituras += 1

        leitura = Counter(tags)
        total_antes = sum(inventario.values())
        for codigo, qtd in leitura.items():
            if qtd > inventario[codigo]:
                inventario[codigo] = qtd
        total_depois = sum(inventario.values())
        novas = total_depois - total_antes

        if novas == 0:
            leituras_sem_novidade += 1
        else:
            leituras_sem_novidade = 0

        if verbose:
            unicos = len(inventario)
            total_lido = len(tags)
            print(f"Leitura {num_leituras}: {total_lido} tags "
                  f"({novas} nova{'s' if novas != 1 else ''}, "
                  f"{unicos} codigo{'s' if unicos != 1 else ''} unico{'s' if unicos != 1 else ''})")

        convergiu = num_leituras >= min_leituras and leituras_sem_novidade >= paciencia
        if convergiu:
            if verbose:
                total = sum(inventario.values())
                unicos = len(inventario)
                print(f"Convergiu em {num_leituras} leituras. "
                      f"Inventario: {total} tags ({unicos} codigos unicos).")
            break

        if num_leituras >= MAX_LEITURAS:
            if verbose:
                total = sum(inventario.values())
                unicos = len(inventario)
                print(f"AVISO: teto de {MAX_LEITURAS} leituras atingido sem "
                      f"convergir. Inventario: {total} tags ({unicos} codigos unicos).")
            break

    return inventario, num_leituras


# ===========================================================================
# Formatacao de saida (texto) — relatorio de recebimento e cupom fiscal
# ===========================================================================

LARGURA_SEPARADOR = 40
LARGURA_NOME_COL = 29   # nome ocupa colunas 1..29; "R$" comeca em 30


def _linha_item(nome, valor):
    """Linha de item do cupom: nome a esquerda, valor a direita."""
    return f"{nome:<{LARGURA_NOME_COL}}R$ {valor:>6.2f}"


def _formatar_lista_tags(tags, catalogo_por_rfid):
    """Lista de tags em ordem estavel, com nome e sufixo xN quando N>1."""
    if hasattr(tags, "items"):
        pares = tags.items()
    else:
        pares = ((t, 1) for t in tags)
    pares = sorted(pares, key=lambda kv: kv[0])
    linhas = []
    for tag, qtd in pares:
        produto = catalogo_por_rfid.get(tag)
        base = f"{produto['nome']} (RFID {tag})" if produto else tag
        linhas.append(f"{base} x{qtd}" if qtd > 1 else base)
    return linhas


def _formatar_divergencia(counter, catalogo_por_rfid):
    """Counter de divergencias como string de uma linha ("nenhum" se vazio)."""
    if not counter:
        return "nenhum"
    partes = []
    for codigo in sorted(counter.keys()):
        qtd = counter[codigo]
        produto = catalogo_por_rfid.get(codigo)
        nome = produto["nome"] if produto else codigo
        partes.append(f"{nome} x{qtd}" if qtd > 1 else nome)
    return ", ".join(partes)


def gerar_relatorio_recebimento(nf, inventario, num_leituras, catalogo):
    """Monta a string do relatorio de recebimento (nao escreve em disco)."""
    if not isinstance(inventario, Counter):
        inventario = Counter(inventario)
    esperados = Counter(nf["itens_esperados"])
    faltando = esperados - inventario
    sobra = inventario - esperados

    por_rfid_idx = {p["rfid"]: p for p in catalogo}
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_esperado = sum(esperados.values())
    total_inventario = sum(inventario.values())

    linhas = []
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append("   RELATORIO DE RECEBIMENTO")
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append(f"NF: {nf['numero']}")
    linhas.append(f"Fornecedor: {nf['fornecedor']}")
    linhas.append(f"Data emissao NF: {nf['data']}")
    linhas.append(f"Data recebimento: {agora}")
    linhas.append("")
    linhas.append(f"{'Itens esperados (NF):':<25}{total_esperado}")
    linhas.append(f"{'Itens recebidos (RFID):':<25}{total_inventario}")
    linhas.append(f"{'Leituras realizadas:':<25}{num_leituras}")
    linhas.append("")
    linhas.append("-" * LARGURA_SEPARADOR)
    linhas.append("ITENS RECEBIDOS:")
    if inventario:
        for descricao in _formatar_lista_tags(inventario, por_rfid_idx):
            linhas.append(f"  - {descricao}")
    else:
        linhas.append("  (nenhum)")
    linhas.append("")
    linhas.append("-" * LARGURA_SEPARADOR)
    linhas.append("DIVERGENCIAS:")
    falt_str = _formatar_divergencia(faltando, por_rfid_idx)
    sobra_str = _formatar_divergencia(sobra, por_rfid_idx)
    linhas.append(f"  {'Faltando:':<10}{falt_str}")
    linhas.append(f"  {'Sobra:':<10}{sobra_str}")
    linhas.append("")
    total_faltando = sum(faltando.values())
    total_sobra = sum(sobra.values())
    if not faltando and not sobra:
        linhas.append("STATUS: OK - Inventario completo")
    else:
        linhas.append(
            f"STATUS: DIVERGENCIA - {total_faltando} faltando, {total_sobra} em sobra"
        )
    linhas.append("=" * LARGURA_SEPARADOR)
    return "\n".join(linhas) + "\n"


def gerar_cupom(itens, total, timestamp=None):
    """Monta a string do cupom fiscal (nao escreve em disco)."""
    if timestamp is None:
        timestamp = datetime.now()
    data_fmt = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    linhas = []
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append("       MERCADO MODELO (SIMULADO)")
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append(f"Data: {data_fmt}")
    linhas.append("")
    linhas.append("-" * LARGURA_SEPARADOR)
    for item in itens:
        if item.get("tipo") == "produto":
            linhas.append(_linha_item(item["nome"], item["preco"]))
        elif item.get("tipo") == "boleto":
            linhas.append(_linha_item(f"BOLETO banco {item['banco']}", item["valor"]))
        else:
            valor = item.get("valor", item.get("preco", 0.0))
            linhas.append(_linha_item("ITEM", valor))
    linhas.append("-" * LARGURA_SEPARADOR)
    linhas.append(_linha_item("TOTAL:", total))
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append("")
    linhas.append("Obrigado pela preferencia!")
    return "\n".join(linhas) + "\n"
