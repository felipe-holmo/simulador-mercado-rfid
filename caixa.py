"""Entry-point Processo 2 (Caixa).

Simula o caixa de um mercado: o cliente passa produtos (EAN-13) e boletos
(FEBRABAN). O sistema auto-detecta o tipo de cada codigo, da baixa no estoque
(data/estoque.json) e imprime um cupom fiscal no terminal.

A "leitura" do caixa NAO usa o leitor RFID: vem do teclado (input) ou de um
arquivo (batch).

Uso:
  python3 caixa.py                            # interativo
  python3 caixa.py --arquivo compra_001.txt   # batch
"""

import argparse

import sistema


def main():
    parser = argparse.ArgumentParser(description="Caixa: le produtos/boletos e gera cupom")
    parser.add_argument("--arquivo", help="TXT com 1 codigo por linha (batch)")
    args = parser.parse_args()

    cat = sistema.carregar_catalogo()
    por_rfid, por_ean = sistema.indices(cat)
    # caixa usa apenas por_ean (cliente escaneia EAN-13 ou barcode FEBRABAN)

    # Banco de estoque (abastecido pelo recebimento). A baixa e feita numa
    # copia em memoria e persistida ao finalizar: uma venda = uma transacao.
    banco = sistema.estoque_carregar()

    itens = []
    total = 0.0

    def processar_codigo(codigo):
        nonlocal total
        # Sanitiza: leitores/operadores enviam espacos, tracos ou pontos junto
        # com os digitos (linha digitavel impressa). Exigencia do PDF do trabalho.
        codigo = "".join(c for c in codigo if c.isdigit())
        if not codigo:
            print("  Codigo invalido: vazio")
            return
        tipo = sistema.detectar(codigo)
        if tipo == "produto":
            p = por_ean.get(codigo)
            if not p:
                print(f"  Produto nao cadastrado: {codigo}")
                return
            # Da baixa no estoque. Sem saldo => nao vende (estoque manda).
            if not sistema.estoque_debitar(banco, codigo, 1):
                print(f"  SEM ESTOQUE: {p['nome']} (saldo: "
                      f"{sistema.estoque_quantidade(banco, codigo)}) - venda nao registrada")
                return
            itens.append({"tipo": "produto", **p})
            total += p["preco"]
            restante = sistema.estoque_quantidade(banco, codigo)
            print(f"  -> {p['nome']} - R$ {p['preco']:.2f}  [estoque restante: {restante}]")
        elif tipo in ("boleto_barra", "boleto_linha"):
            try:
                b = sistema.parse_boleto(codigo)
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
                if sistema.detectar(codigo) == "finalizar":
                    break
                processar_codigo(codigo)
    else:
        print("=== CAIXA ABERTO ===")
        while True:
            codigo = input("Ler codigo: ").strip()
            if sistema.detectar(codigo) == "finalizar":
                break
            processar_codigo(codigo)

    # Persiste a baixa do estoque (uma venda = uma transacao).
    sistema.estoque_salvar(banco)

    print(sistema.gerar_cupom(itens, total))


if __name__ == "__main__":
    main()
