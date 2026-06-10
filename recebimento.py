"""Entry-point Processo 1 (Recebimento).

Reconcilia o inventario lido pelo leitor RFID contra a Nota Fiscal esperada,
imprime o relatorio de recebimento no terminal e credita o que chegou
fisicamente no estoque (data/estoque.json).

Uso:
  python3 recebimento.py --nf data/nf/nf_001_normal.json
  python3 recebimento.py --nf data/nf/nf_002_com_falta.json --reset-estoque

Exit code:
  0  se nao houver divergencia (inventario bate com a NF)
  1  se houver qualquer tag faltando ou em sobra
"""

import argparse
import json
import sys
from collections import Counter

import sistema


def main():
    parser = argparse.ArgumentParser(description="Recebimento: reconcilia RFID contra NF")
    parser.add_argument("--nf", required=True, help="Path para NF JSON")
    parser.add_argument("--rfid-url", default="http://127.0.0.1:3000")
    parser.add_argument("--reset-estoque", action="store_true",
                        help="Zera o estoque antes de creditar (util para demos)")
    args = parser.parse_args()

    # 1. Carregar catalogo e NF.
    catalogo = sistema.carregar_catalogo()
    with open(args.nf, "r", encoding="utf-8") as f:
        nf = json.load(f)

    # 2. Ler o leitor RFID ate o inventario convergir.
    client = sistema.RFIDClient(args.rfid_url)
    inventario, num_leituras = sistema.reconciliar(client, verbose=True)

    # 3. Comparar inventario lido contra o esperado na NF (Counter - Counter).
    esperados = Counter(nf["itens_esperados"])
    faltando = esperados - inventario
    sobra = inventario - esperados

    # 4. Gerar e imprimir o relatorio (apenas no terminal).
    print(sistema.gerar_relatorio_recebimento(nf, inventario, num_leituras, catalogo))

    # 5. Creditar o que chegou fisicamente no estoque (RFID -> EAN-13).
    banco = {} if args.reset_estoque else sistema.estoque_carregar()
    por_rfid_idx, _ = sistema.indices(catalogo)
    creditadas = 0
    nao_cadastradas = Counter()
    for rfid_code, qtd in inventario.items():
        produto = por_rfid_idx.get(rfid_code)
        if produto:
            sistema.estoque_creditar(banco, produto["ean13"], produto["nome"], qtd)
            creditadas += qtd
        else:
            nao_cadastradas[rfid_code] += qtd
    estoque_path = sistema.estoque_salvar(banco)
    print(f"Estoque atualizado: +{creditadas} unidade(s) creditada(s) em {estoque_path}")
    if nao_cadastradas:
        total_nc = sum(nao_cadastradas.values())
        print(f"  Aviso: {total_nc} tag(s) sem cadastro no catalogo NAO foram "
              f"estocadas: {', '.join(sorted(nao_cadastradas))}")

    # 6. Exit code: 0 quando tudo bate, 1 quando ha qualquer divergencia.
    if faltando or sobra:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
