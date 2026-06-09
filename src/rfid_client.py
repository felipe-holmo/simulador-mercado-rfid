"""Cliente HTTP do servidor RFID + reconciliacao adaptativa."""

import urllib.request
import json
from collections import Counter

DEFAULT_RFID_URL = "http://127.0.0.1:3000"

# Teto absoluto de leituras: evita loop infinito caso o mock/`.exe` degenere
# e nunca convirja (HANDOFF secao 11).
MAX_LEITURAS = 20


class RFIDClient:
    def __init__(self, base_url=DEFAULT_RFID_URL):
        self.base_url = base_url

    def ler_tags(self) -> list:
        """GET /tags. Retorna a lista de tags lidas (pode ter duplicatas)."""
        url = self.base_url.rstrip("/") + "/tags"
        with urllib.request.urlopen(url) as resposta:
            corpo = resposta.read().decode("utf-8")
        return json.loads(corpo)["tags"]


def reconciliar(client: RFIDClient,
                min_leituras: int = 3,
                paciencia: int = 2,
                verbose: bool = True) -> tuple:
    """Le tags repetidamente ate convergir.

    O inventario e um Counter — o RFID emulado expoe produtos duplicados
    (varias tags fisicas com o MESMO codigo). Cada leitura pode trazer
    cada tag um numero variavel de vezes por causa de falhas estatisticas
    de leitura. Mantemos, por codigo, o MAXIMO ja observado entre todas
    as leituras — esse e o melhor estimador da quantidade real de tags
    fisicas presentes.

    Para quando:
      - ja fizemos >= min_leituras E
      - as ultimas `paciencia` leituras consecutivas nao trouxeram
        nenhuma contagem nova (nem codigo novo, nem aumento de quantidade).

    Possui um teto absoluto (MAX_LEITURAS) para nunca rodar infinito mesmo
    com um mock degenerado; ao bater o teto, retorna o inventario parcial
    emitindo um aviso (quando verbose).

    Retorna (inventario, num_leituras).
    """
    inventario = Counter()
    num_leituras = 0
    leituras_sem_novidade = 0

    while True:
        tags = client.ler_tags()
        num_leituras += 1

        leitura = Counter(tags)
        total_antes = sum(inventario.values())
        # Max-merge: por codigo, mantemos o maximo ja observado.
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
