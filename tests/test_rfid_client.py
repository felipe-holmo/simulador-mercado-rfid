"""Testes do modulo `src.rfid_client`.

Estrategia: mockamos `urllib.request.urlopen` com `unittest.mock.patch` para
retornar respostas JSON controladas (via `io.BytesIO`), sem depender do mock
HTTP real. Cobertura: parse do JSON, convergencia, min_leituras, recuperacao
de tag perdida e respeito ao teto MAX_LEITURAS.
"""

import io
import json
import unittest
from collections import Counter
from unittest import mock

from src import rfid_client
from src.rfid_client import RFIDClient, reconciliar


def _resposta(tags):
    """Cria um objeto compativel com o context manager de urlopen."""
    corpo = json.dumps({"tags": tags}).encode("utf-8")
    fake = io.BytesIO(corpo)
    # urlopen e usado como context manager (with ... as resp): BytesIO ja
    # suporta __enter__/__exit__ e read(), bastando para o nosso uso.
    return fake


class TestLerTags(unittest.TestCase):

    @mock.patch("src.rfid_client.urllib.request.urlopen")
    def test_ler_tags_parse_json_corretamente(self, mock_urlopen):
        """ler_tags faz GET em /tags e parseia a lista de tags do JSON."""
        mock_urlopen.return_value = _resposta(["A", "B", "B", "C"])
        client = RFIDClient()
        tags = client.ler_tags()
        self.assertEqual(tags, ["A", "B", "B", "C"])
        # Confirma que chamou a URL com sufixo /tags.
        url_chamada = mock_urlopen.call_args[0][0]
        self.assertTrue(url_chamada.endswith("/tags"))


class TestReconciliar(unittest.TestCase):

    @mock.patch("src.rfid_client.RFIDClient.ler_tags")
    def test_reconciliar_para_apos_convergencia(self, mock_ler):
        """Reconciliacao para quando as leituras param de trazer novidade."""
        # Sempre as mesmas N tags -> nenhuma novidade apos a 1a leitura.
        mock_ler.return_value = ["A", "B", "C"]
        inventario, num_leituras = reconciliar(RFIDClient(), verbose=False)
        # Inventario virou Counter: cada codigo aparece 1x por leitura.
        self.assertEqual(inventario, Counter({"A": 1, "B": 1, "C": 1}))
        # min_leituras=3 + paciencia=2: converge logo no minimo possivel.
        self.assertEqual(num_leituras, 3)

    @mock.patch("src.rfid_client.RFIDClient.ler_tags")
    def test_reconciliar_mantem_max_de_duplicatas_por_codigo(self, mock_ler):
        """Mantem a quantidade (duplicatas) de cada codigo no inventario."""
        # Tag "A" aparece 3x em todas as leituras (modelo: 3 unidades fisicas).
        # Tag "B" aparece 1x. Inventario final deve refletir as quantidades.
        mock_ler.return_value = ["A", "A", "A", "B"]
        inventario, _ = reconciliar(RFIDClient(), verbose=False)
        self.assertEqual(inventario, Counter({"A": 3, "B": 1}))

    @mock.patch("src.rfid_client.RFIDClient.ler_tags")
    def test_reconciliar_aplica_max_merge_entre_leituras(self, mock_ler):
        """Usa o maximo ja visto de cada tag entre leituras (max-merge)."""
        # 1a leitura: A x1 (falha leu so 1 das 3). 2a: A x3 (leu todas).
        # 3a+: A x2 (perdeu 1). Esperado: max ja observado -> A x3.
        mock_ler.side_effect = [
            ["A"],
            ["A", "A", "A"],
            ["A", "A"],
            ["A", "A"],
            ["A", "A"],
        ]
        inventario, _ = reconciliar(RFIDClient(), verbose=False)
        self.assertEqual(inventario["A"], 3)

    @mock.patch("src.rfid_client.RFIDClient.ler_tags")
    def test_reconciliar_respeita_min_leituras(self, mock_ler):
        """Faz pelo menos min_leituras mesmo que ja tenha convergido."""
        # 1a leitura ja traz tudo, mas min_leituras obriga repetir.
        mock_ler.return_value = ["A", "B", "C"]
        _, num_leituras = reconciliar(RFIDClient(), min_leituras=3,
                                      paciencia=1, verbose=False)
        self.assertGreaterEqual(num_leituras, 3)

    @mock.patch("src.rfid_client.RFIDClient.ler_tags")
    def test_reconciliar_recupera_tag_perdida_em_leitura_subsequente(self, mock_ler):
        """Recupera tag que so apareceu numa leitura posterior."""
        # 9 tags na 1a leitura; a 10a aparece so na 2a leitura.
        nove = [f"T{i}" for i in range(9)]
        dez = nove + ["T9"]
        mock_ler.side_effect = [nove, dez, dez, dez, dez, dez]
        inventario, _ = reconciliar(RFIDClient(), verbose=False)
        self.assertEqual(len(inventario), 10)
        self.assertIn("T9", inventario)

    @mock.patch("src.rfid_client.RFIDClient.ler_tags")
    def test_reconciliar_respeita_max_leituras(self, mock_ler):
        """Para no teto MAX_LEITURAS quando a leitura nunca converge."""
        # Sempre uma tag nova -> nunca convergiria; deve parar no teto.
        contador = {"n": 0}

        def sempre_nova():
            contador["n"] += 1
            return [f"T{contador['n']}"]

        mock_ler.side_effect = lambda: sempre_nova()
        _, num_leituras = reconciliar(RFIDClient(), verbose=False)
        self.assertEqual(num_leituras, rfid_client.MAX_LEITURAS)


if __name__ == "__main__":
    unittest.main()
