"""Testes do modulo `src.catalog`.

Foco:
- Carga do JSON real em `data/catalog.json` (10 produtos da spec).
- Construcao dos dois indices (por_rfid / por_ean) com cardinalidade certa.
- Lookups linears: hit por RFID, miss por RFID, hit por EAN.
"""

import unittest

from src import catalog


class TestCatalog(unittest.TestCase):

    def setUp(self):
        # Carrega uma vez por teste — o catalogo e pequeno, IO e barato.
        self.catalogo = catalog.carregar()

    def test_carrega_10_produtos(self):
        # HANDOFF secao 4 fixa 10 produtos no catalogo.
        self.assertEqual(len(self.catalogo), 10)

    def test_indices_completos(self):
        por_rfid_idx, por_ean_idx = catalog.indices(self.catalogo)
        # Sem colisoes nas chaves: 10 produtos -> 10 entradas em cada indice.
        self.assertEqual(len(por_rfid_idx), 10)
        self.assertEqual(len(por_ean_idx), 10)

    def test_lookup_por_rfid_existente(self):
        produto = catalog.por_rfid(self.catalogo, "123456789012")
        self.assertIsNotNone(produto)
        self.assertEqual(produto["nome"], "Cafe Pilao 500g")
        self.assertEqual(produto["ean13"], "7890000000017")
        self.assertEqual(produto["preco"], 18.90)

    def test_lookup_por_rfid_inexistente_retorna_none(self):
        self.assertIsNone(catalog.por_rfid(self.catalogo, "000000000000"))

    def test_lookup_por_ean_existente(self):
        produto = catalog.por_ean(self.catalogo, "7890000000024")
        self.assertIsNotNone(produto)
        self.assertEqual(produto["nome"], "Leite Itambe 1L")
        self.assertEqual(produto["rfid"], "987654321098")


if __name__ == "__main__":
    unittest.main()
