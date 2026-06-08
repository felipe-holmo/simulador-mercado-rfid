"""Cliente HTTP do servidor RFID + reconciliacao adaptativa."""

import urllib.request
import json

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

    Para quando:
      - ja fizemos >= min_leituras E
      - as ultimas `paciencia` leituras consecutivas nao trouxeram tag nova.

    Possui um teto absoluto (MAX_LEITURAS) para nunca rodar infinito mesmo
    com um mock degenerado; ao bater o teto, retorna o inventario parcial
    emitindo um aviso (quando verbose).

    Retorna (inventario, num_leituras).
    """
    inventario = set()
    num_leituras = 0
    leituras_sem_novidade = 0

    while True:
        tags = client.ler_tags()
        num_leituras += 1

        antes = len(inventario)
        inventario.update(tags)
        novas = len(inventario) - antes
        duplicatas = len(tags) - len(set(tags))

        if novas == 0:
            leituras_sem_novidade += 1
        else:
            leituras_sem_novidade = 0

        if verbose:
            print(f"Leitura {num_leituras}: {len(tags)} tags "
                  f"({novas} nova{'s' if novas != 1 else ''}, "
                  f"{duplicatas} duplicata{'s' if duplicatas != 1 else ''})")

        convergiu = num_leituras >= min_leituras and leituras_sem_novidade >= paciencia
        if convergiu:
            if verbose:
                print(f"Convergiu em {num_leituras} leituras. "
                      f"Inventario: {len(inventario)} tags unicas.")
            break

        if num_leituras >= MAX_LEITURAS:
            if verbose:
                print(f"AVISO: teto de {MAX_LEITURAS} leituras atingido sem "
                      f"convergir. Inventario: {len(inventario)} tags unicas.")
            break

    return inventario, num_leituras
