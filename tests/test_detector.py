"""Testes do modulo `src.detector`.

Cobertura: 1 teste por outcome (5) + 3 cobertura de bordas
("FIM" case-insensitive, codigo com letras, codigo vazio) = 8 testes.
"""

import unittest

from src import detector


class TestDetector(unittest.TestCase):

    def test_detectar_produto_ean13(self):
        """13 digitos sao classificados como 'produto'."""
        # 13 digitos -> produto. Usamos um EAN-13 real do catalogo.
        self.assertEqual(detector.detectar("7890000000017"), "produto")

    def test_detectar_boleto_codigo_de_barras_44(self):
        """44 digitos sao classificados como 'boleto_barra'."""
        # 44 digitos -> boleto codigo de barras.
        self.assertEqual(detector.detectar("3" * 44), "boleto_barra")

    def test_detectar_boleto_linha_digitavel_47(self):
        """47 digitos sao classificados como 'boleto_linha'."""
        # 47 digitos -> boleto linha digitavel.
        self.assertEqual(
            detector.detectar("34191790010104351004791020150008991230000012345"),
            "boleto_linha",
        )

    def test_detectar_finalizar(self):
        """A palavra 'FIM' e classificada como 'finalizar'."""
        self.assertEqual(detector.detectar("FIM"), "finalizar")

    def test_detectar_invalido_tamanho_errado(self):
        """Tamanho desconhecido (3 digitos) e classificado como 'invalido'."""
        # 3 digitos nao casa nenhum tamanho conhecido.
        self.assertEqual(detector.detectar("123"), "invalido")

    def test_detectar_fim_case_insensitive(self):
        """'FIM' e reconhecido em qualquer caixa (fim, Fim, fIm...)."""
        # Contrato (HANDOFF 5.3): codigo.upper() == "FIM".
        for variacao in ("FIM", "fim", "Fim", "fIm", "FiM"):
            with self.subTest(codigo=variacao):
                self.assertEqual(detector.detectar(variacao), "finalizar")

    def test_detectar_codigo_com_letras_invalido(self):
        """Codigo com letras nao e produto: vira 'invalido'."""
        # 13 chars mas com letras -> nao passa em isdigit.
        self.assertEqual(detector.detectar("789000000001A"), "invalido")

    def test_detectar_codigo_vazio_invalido(self):
        """Codigo vazio e classificado como 'invalido'."""
        # "".upper() == "FIM" e False; "".isdigit() tambem e False.
        self.assertEqual(detector.detectar(""), "invalido")


if __name__ == "__main__":
    unittest.main()
