"""Testes do modulo `src.estoque` (banco de estoque persistente).

Estrategia: usamos arquivos temporarios (tempfile) para nao tocar no
`data/estoque.json` real. Cobertura: arquivo inexistente, credito (com e
sem produto pre-existente), debito (saldo suficiente e insuficiente),
consulta de quantidade e round-trip salvar/carregar.
"""

import json
import os
import tempfile
import unittest

from src import estoque


class TestEstoque(unittest.TestCase):

    def setUp(self):
        # Caminho temporario unico por teste (removido no tearDown).
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)  # queremos testar tambem a ausencia do arquivo

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_carregar_arquivo_inexistente_retorna_vazio(self):
        """Quando o banco ainda nao existe, carregar retorna dict vazio."""
        self.assertEqual(estoque.carregar(self.path), {})

    def test_creditar_cria_entrada_nova(self):
        """Creditar um produto inexistente cria a entrada com a quantidade."""
        banco = {}
        resultante = estoque.creditar(banco, "789", "Cafe", 3)
        self.assertEqual(resultante, 3)
        self.assertEqual(banco["789"], {"nome": "Cafe", "quantidade": 3})

    def test_creditar_acumula_em_entrada_existente(self):
        """Creditar de novo soma a quantidade (entradas sucessivas)."""
        banco = {"789": {"nome": "Cafe", "quantidade": 2}}
        resultante = estoque.creditar(banco, "789", "Cafe", 3)
        self.assertEqual(resultante, 5)

    def test_quantidade_de_produto_inexistente_e_zero(self):
        """Produto sem entrada no banco tem quantidade 0."""
        self.assertEqual(estoque.quantidade({}, "000"), 0)

    def test_debitar_com_saldo_suficiente(self):
        """Debitar com saldo retorna True e reduz a quantidade."""
        banco = {"789": {"nome": "Cafe", "quantidade": 2}}
        self.assertTrue(estoque.debitar(banco, "789", 1))
        self.assertEqual(estoque.quantidade(banco, "789"), 1)

    def test_debitar_sem_saldo_nao_altera_e_retorna_false(self):
        """Sem saldo, debitar retorna False e nao deixa quantidade negativa."""
        banco = {"789": {"nome": "Cafe", "quantidade": 0}}
        self.assertFalse(estoque.debitar(banco, "789", 1))
        self.assertEqual(estoque.quantidade(banco, "789"), 0)

    def test_debitar_produto_inexistente_retorna_false(self):
        """Debitar produto que nem existe no banco retorna False."""
        self.assertFalse(estoque.debitar({}, "000", 1))

    def test_salvar_e_carregar_roundtrip(self):
        """O que e salvo em disco e relido identico (round-trip)."""
        banco = {"789": {"nome": "Cafe", "quantidade": 3}}
        estoque.salvar(banco, self.path)
        self.assertEqual(estoque.carregar(self.path), banco)
        # Confirma que o arquivo e JSON valido com utf-8.
        with open(self.path, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), banco)


if __name__ == "__main__":
    unittest.main()
