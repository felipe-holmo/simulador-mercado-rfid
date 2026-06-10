"""Entry-point Processo 1 (Recebimento).

Reconcilia o inventario lido pelo leitor RFID contra a Nota Fiscal esperada
e gera um relatorio de recebimento (terminal + arquivo TXT).

Uso:
  python3 bin/recebimento.py --nf data/nf/nf_001_normal.json
  python3 bin/recebimento.py --nf data/nf/nf_002_com_falta.json --rfid-url http://127.0.0.1:8080

Exit code:
  0  se nao houver divergencia (inventario bate com a NF)
  1  se houver qualquer tag faltando ou em sobra
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import catalog, rfid_client, relatorios, estoque


def main():
    parser = argparse.ArgumentParser(description="Recebimento: reconcilia RFID contra NF")
    parser.add_argument("--nf", required=True, help="Path para NF JSON")
    parser.add_argument("--rfid-url", default="http://127.0.0.1:3000")
    parser.add_argument("--reset-estoque", action="store_true",
                        help="Zera o estoque antes de creditar (util para demos)")
    args = parser.parse_args()

    # 1. Carregar catalogo e NF.
    catalogo = catalog.carregar()
    with open(args.nf, "r", encoding="utf-8") as f:
        nf = json.load(f)

    # 2. Ler o leitor RFID ate o inventario convergir.
    client = rfid_client.RFIDClient(args.rfid_url)
    inventario, num_leituras = rfid_client.reconciliar(client, verbose=True)

    # 3. Comparar inventario lido contra o esperado na NF.
    # itens_esperados pode ter codigos repetidos (multiplas unidades do mesmo
    # produto). Counter - Counter ja cuida das quantidades:
    #   Counter({A:3}) - Counter({A:1}) == Counter({A:2})
    esperados = Counter(nf["itens_esperados"])
    faltando = esperados - inventario
    sobra = inventario - esperados

    # 4. Gerar relatorio, imprimir e salvar.
    conteudo = relatorios.gerar_relatorio_recebimento(nf, inventario, num_leituras, catalogo)
    print(conteudo)
    path = relatorios.salvar_relatorio(conteudo, nf["numero"])
    print(f"Relatorio salvo em: {path}")

    # 5. Creditar o que chegou FISICAMENTE no estoque (o "banco").
    # O inventario e por RFID; convertemos RFID -> EAN-13 pelo catalogo,
    # pois o estoque (consumido pelo caixa) e chaveado por EAN-13.
    banco = {} if args.reset_estoque else estoque.carregar()
    por_rfid_idx, _ = catalog.indices(catalogo)
    creditadas = 0
    nao_cadastradas = Counter()
    for rfid_code, qtd in inventario.items():
        produto = por_rfid_idx.get(rfid_code)
        if produto:
            estoque.creditar(banco, produto["ean13"], produto["nome"], qtd)
            creditadas += qtd
        else:
            nao_cadastradas[rfid_code] += qtd
    estoque_path = estoque.salvar(banco)
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
