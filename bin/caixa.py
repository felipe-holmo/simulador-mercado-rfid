"""Entry-point Processo 2 (Caixa).

Simula o caixa de um mercado: o cliente passa produtos (EAN-13) e boletos
(FEBRABAN). O sistema auto-detecta o tipo de cada codigo, monta o carrinho e
gera um cupom fiscal simulado (terminal + arquivo TXT).

A "leitura" do caixa NAO usa o leitor RFID: vem do teclado (input) ou de um
arquivo (batch). Por isso este modulo nao importa rfid_client.

Uso:
  python3 bin/caixa.py                            # interativo
  python3 bin/caixa.py --arquivo compra_001.txt   # batch
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import catalog, febraban, detector, relatorios, estoque


def main():
    parser = argparse.ArgumentParser(description="Caixa: le produtos/boletos e gera cupom")
    parser.add_argument("--arquivo", help="TXT com 1 codigo por linha (batch)")
    args = parser.parse_args()

    cat = catalog.carregar()
    por_rfid, por_ean = catalog.indices(cat)  # ordem segue secao 5.1
    # caixa usa apenas por_ean (cliente escaneia EAN-13 ou barcode FEBRABAN, nao RFID)

    # Banco de estoque (abastecido pelo recebimento). A baixa e feita numa
    # copia em memoria durante a venda e persistida ao finalizar (FIM):
    # uma venda = uma transacao.
    banco = estoque.carregar()

    itens = []
    total = 0.0

    def processar_codigo(codigo):
        nonlocal total
        # Sanitiza: leitores fisicos e operadores costumam enviar espacos,
        # tracos ou pontos junto com os digitos (linha digitavel impressa).
        # Exigencia explicita do PDF do trabalho final.
        codigo = "".join(c for c in codigo if c.isdigit())
        if not codigo:
            print("  Codigo invalido: vazio")
            return
        tipo = detector.detectar(codigo)
        if tipo == "produto":
            p = por_ean.get(codigo)
            if not p:
                print(f"  Produto nao cadastrado: {codigo}")
                return
            # Da baixa no estoque. Sem saldo => nao vende (estoque manda).
            if not estoque.debitar(banco, codigo, 1):
                print(f"  SEM ESTOQUE: {p['nome']} (saldo: "
                      f"{estoque.quantidade(banco, codigo)}) - venda nao registrada")
                return
            itens.append({"tipo": "produto", **p})
            total += p["preco"]
            restante = estoque.quantidade(banco, codigo)
            print(f"  -> {p['nome']} - R$ {p['preco']:.2f}  [estoque restante: {restante}]")
        elif tipo in ("boleto_barra", "boleto_linha"):
            try:
                b = febraban.parse(codigo)
                itens.append(b)
                total += b["valor"]
                print(f"  -> BOLETO banco {b['banco']} - R$ {b['valor']:.2f}")
            except ValueError as e:
                print(f"  Boleto invalido: {e}")
        else:
            print(f"  Codigo invalido: {codigo}")
        print(f"  Subtotal: R$ {total:.2f}")

    if args.arquivo:
        with open(args.arquivo, "r", encoding="utf-8") as f:
            for linha in f:
                codigo = linha.strip()
                if not codigo:
                    continue
                if detector.detectar(codigo) == "finalizar":
                    break
                processar_codigo(codigo)
    else:
        print("=== CAIXA ABERTO ===")
        while True:
            codigo = input("Ler codigo: ").strip()
            if detector.detectar(codigo) == "finalizar":
                break
            processar_codigo(codigo)

    # Persiste a baixa do estoque (uma venda = uma transacao).
    estoque_path = estoque.salvar(banco)

    conteudo = relatorios.gerar_cupom(itens, total)
    path = relatorios.salvar_cupom(conteudo)
    print(conteudo)
    print(f"\nCupom salvo em: {path}")
    print(f"Estoque atualizado em: {estoque_path}")


if __name__ == "__main__":
    main()
