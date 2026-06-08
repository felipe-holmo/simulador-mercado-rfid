"""Geracao de relatorios TXT (recebimento) e cupons TXT (caixa).

Modulo de IO puro: monta strings que replicam exatamente os templates
do HANDOFF.md secao 7 e grava arquivos em `output/relatorios/` e
`output/cupons/`.

Larguras (validadas contra o template do HANDOFF):
  - Separadores `=` e `-`: 40 colunas
  - Linhas de item do cupom: 38 colunas
      nome:<29 + "R$ " + valor:>6.2f
  - Linhas de contadores do relatorio: numero comeca na coluna 26
"""

from datetime import datetime
from pathlib import Path


# Raiz do repo (relatorios.py vive em src/, sobe um nivel).
REPO_ROOT = Path(__file__).parent.parent
RELATORIOS_DIR = REPO_ROOT / "output" / "relatorios"
CUPONS_DIR = REPO_ROOT / "output" / "cupons"

# Constantes de largura, conferidas no HANDOFF secao 7.
LARGURA_SEPARADOR = 40
LARGURA_LINHA_ITEM = 38
LARGURA_NOME_COL = 29   # nome ocupa colunas 1..29; "R$" comeca em 30


def _linha_item(nome, valor):
    """Formata uma linha de item do cupom (nome a esquerda, valor a direita).

    Caso o nome seja maior que LARGURA_NOME_COL, o `<29` apenas garante
    o minimo — strings longas estouram a largura mas nao quebram o codigo.
    """
    return f"{nome:<{LARGURA_NOME_COL}}R$ {valor:>6.2f}"


def _formatar_lista_tags(tags, catalogo_por_rfid):
    """Devolve a lista de tags em ordem estavel, com nome quando disponivel.

    Tags conhecidas (presentes no catalogo) saem como `Nome (RFID xxx)`.
    Tags desconhecidas saem so como o RFID. A ordem segue o sorted das
    tags para garantir output deterministico (mesmo input -> mesmo output).
    """
    linhas = []
    for tag in sorted(tags):
        produto = catalogo_por_rfid.get(tag)
        if produto:
            linhas.append(f"{produto['nome']} (RFID {tag})")
        else:
            linhas.append(tag)
    return linhas


def gerar_relatorio_recebimento(nf, inventario, num_leituras, catalogo):
    """Monta a string completa do relatorio de recebimento.

    Argumentos:
      nf            dict carregado de data/nf/*.json
                    (chaves: numero, fornecedor, data, itens_esperados)
      inventario    set de RFIDs efetivamente lidos pelo leitor
      num_leituras  numero de chamadas a /tags ate convergir
      catalogo      lista de produtos (carregada por catalog.carregar)

    Retorna a string formatada (NAO escreve em disco).
    """
    esperados = set(nf["itens_esperados"])
    faltando = esperados - inventario
    sobra = inventario - esperados

    por_rfid_idx = {p["rfid"]: p for p in catalogo}
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    linhas = []
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append("   RELATORIO DE RECEBIMENTO")
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append(f"NF: {nf['numero']}")
    linhas.append(f"Fornecedor: {nf['fornecedor']}")
    linhas.append(f"Data emissao NF: {nf['data']}")
    linhas.append(f"Data recebimento: {agora}")
    linhas.append("")
    # Os 3 contadores tem o numero comecando na coluna 26 (label + padding ate 25).
    linhas.append(f"{'Itens esperados (NF):':<25}{len(esperados)}")
    linhas.append(f"{'Itens recebidos (RFID):':<25}{len(inventario)}")
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
    # Padding "Faltando:" e "Sobra:   " ate 10 chars para alinhar (HANDOFF secao 7).
    falt_str = ", ".join(sorted(faltando)) if faltando else "nenhum"
    sobra_str = ", ".join(sorted(sobra)) if sobra else "nenhum"
    linhas.append(f"  {'Faltando:':<10}{falt_str}")
    linhas.append(f"  {'Sobra:':<10}{sobra_str}")
    linhas.append("")
    if not faltando and not sobra:
        linhas.append("STATUS: OK - Inventario completo")
    else:
        linhas.append(
            f"STATUS: DIVERGENCIA - {len(faltando)} faltando, {len(sobra)} em sobra"
        )
    linhas.append("=" * LARGURA_SEPARADOR)
    # \n final para o arquivo terminar com newline (convencao POSIX).
    return "\n".join(linhas) + "\n"


def salvar_relatorio(conteudo, nf_numero):
    """Grava `conteudo` em output/relatorios/relatorio_<nf_numero>.txt.

    Cria o diretorio pai se nao existir. Sempre utf-8 explicito (HANDOFF
    secao 11 alerta sobre Windows). Retorna o Path do arquivo escrito.
    """
    RELATORIOS_DIR.mkdir(parents=True, exist_ok=True)
    path = RELATORIOS_DIR / f"relatorio_{nf_numero}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return path


def gerar_cupom(itens, total, timestamp=None):
    """Monta a string do cupom fiscal.

    Argumentos:
      itens     lista de dicts. Cada item tem `tipo` ("produto" ou
                "boleto") e os campos especificos:
                - produto: chaves `nome` e `preco`
                - boleto:  chaves `banco` e `valor`
      total     soma ja calculada (passada pronta pelo bin/caixa.py)
      timestamp datetime opcional para reprodutibilidade nos testes;
                quando None, usa `datetime.now()`.

    Retorna a string formatada (NAO escreve em disco).
    """
    if timestamp is None:
        timestamp = datetime.now()
    data_fmt = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    linhas = []
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append("       MERCADO KAMA (SIMULADO)")
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
            # Defensivo: tipo desconhecido vira "ITEM" generico.
            valor = item.get("valor", item.get("preco", 0.0))
            linhas.append(_linha_item("ITEM", valor))
    linhas.append("-" * LARGURA_SEPARADOR)
    linhas.append(_linha_item("TOTAL:", total))
    linhas.append("=" * LARGURA_SEPARADOR)
    linhas.append("")
    linhas.append("Obrigado pela preferencia!")
    return "\n".join(linhas) + "\n"


def salvar_cupom(conteudo, timestamp=None):
    """Grava `conteudo` em output/cupons/cupom_<YYYY-MM-DD_HHMMSS>.txt.

    O timestamp do nome do arquivo e gerado pela mesma `datetime.now()`
    que (idealmente) foi usada no `gerar_cupom`. Para garantir consistencia
    estrita, passe o mesmo `timestamp` nas duas chamadas.
    """
    if timestamp is None:
        timestamp = datetime.now()
    CUPONS_DIR.mkdir(parents=True, exist_ok=True)
    nome = f"cupom_{timestamp.strftime('%Y-%m-%d_%H%M%S')}.txt"
    path = CUPONS_DIR / nome
    with open(path, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return path
