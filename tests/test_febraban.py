"""Testes do modulo `src.febraban`.

Estrategia: boletos reais raramente tem DV Mod 10 valido para teste, entao
geramos boletos sinteticos calculando os DVs com `febraban._calcular_dv_mod10`
(HANDOFF secao 5.2). Cobertura: parse 47, parse 44, DV invalido, tamanho
errado e extracao de valor.
"""

import unittest

from src import febraban


def _montar_linha_digitavel(banco="341", valor_centavos=12345):
    """Monta uma linha digitavel de 47 digitos com os 3 DVs Mod 10 corretos.

    Estrutura (indices 0-based):
      - Campo 1: dados [0:9] + DV[9]
      - Campo 2: dados [10:20] + DV[20]
      - Campo 3: dados [21:31] + DV[31]
      - DV geral (Mod 11) no indice 32 (nao validado: usamos "0")
      - Fator vencimento (4) + valor (10) em [33:47]
    """
    campo1_dados = (banco + "917900")[:9].ljust(9, "0")
    campo2_dados = "1043510047"
    campo3_dados = "9102015000"
    dv_geral = "0"
    fator_vencimento = "0000"
    valor = str(valor_centavos).zfill(10)

    dv1 = str(febraban._calcular_dv_mod10(campo1_dados))
    dv2 = str(febraban._calcular_dv_mod10(campo2_dados))
    dv3 = str(febraban._calcular_dv_mod10(campo3_dados))

    return (campo1_dados + dv1
            + campo2_dados + dv2
            + campo3_dados + dv3
            + dv_geral
            + fator_vencimento + valor)


class TestFebraban(unittest.TestCase):

    def test_parse_linha_digitavel_47_validos(self):
        """Parseia linha digitavel de 47 digitos e extrai banco e valor."""
        linha = _montar_linha_digitavel(banco="341", valor_centavos=12345)
        self.assertEqual(len(linha), 47)
        resultado = febraban.parse(linha)
        self.assertEqual(resultado["tipo"], "boleto")
        self.assertEqual(resultado["banco"], "341")
        self.assertAlmostEqual(resultado["valor"], 123.45, places=2)
        self.assertEqual(resultado["codigo_original"], linha)

    def test_parse_codigo_barras_44_validos(self):
        """Parseia codigo de barras de 44 digitos e extrai banco e valor."""
        # 44 digitos: aceito por tamanho (DV Mod 11 nao validado).
        # Estrutura FEBRABAN: banco(3)+moeda(1)+dv(1)+fator_venc(4)+valor(10)+livre(25).
        # Valor em codigo[9:19]; usamos "0000012345" -> R$ 123,45.
        codigo = "341" + "0" + "0" + "0000" + "0000012345" + "0" * 25
        self.assertEqual(len(codigo), 44)
        resultado = febraban.parse(codigo)
        self.assertEqual(resultado["tipo"], "boleto")
        self.assertEqual(resultado["banco"], "341")
        self.assertAlmostEqual(resultado["valor"], 123.45, places=2)

    def test_parse_dv_invalido_levanta(self):
        """DV Mod 10 invalido faz o parse levantar ValueError."""
        # Pega uma linha valida e troca 1 digito de dados de um campo,
        # invalidando o DV Mod 10.
        linha = list(_montar_linha_digitavel())
        linha[0] = str((int(linha[0]) + 1) % 10)
        linha = "".join(linha)
        with self.assertRaises(ValueError):
            febraban.parse(linha)

    def test_parse_tamanho_errado_levanta(self):
        """Tamanho fora de 44/47 digitos levanta ValueError."""
        with self.assertRaises(ValueError):
            febraban.parse("123")

    def test_extrair_valor_correto(self):
        """Extrai o valor monetario na posicao certa (casos 47 e 44 digitos)."""
        # 47 digitos: valor em codigo[37:47].
        linha = _montar_linha_digitavel(valor_centavos=12345)
        self.assertAlmostEqual(febraban.extrair_valor(linha), 123.45, places=2)
        # 44 digitos: valor em codigo[9:19] (apos banco/moeda/dv/fator_venc).
        codigo44 = "0" * 9 + "0000012345" + "0" * 25
        self.assertEqual(len(codigo44), 44)
        self.assertAlmostEqual(febraban.extrair_valor(codigo44), 123.45, places=2)

    def test_parse_codigo_barras_valor_real(self):
        """Barcode 44-dig oficial: valor lido na posicao FEBRABAN correta."""
        # Cenario realista: scanner fisico le um barcode 44-dig com estrutura
        # oficial FEBRABAN. Documenta a posicao correta do valor (regressao
        # do bug de offset que existia em [5:14]).
        banco = "341"
        moeda = "9"
        dv_geral = "8"  # Mod 11 nao validado pelo parser
        fator_venc = "0000"
        valor = "0000012345"  # R$ 123,45
        campo_livre = "1790010104351004910201500"
        codigo = banco + moeda + dv_geral + fator_venc + valor + campo_livre
        self.assertEqual(len(codigo), 44)
        resultado = febraban.parse(codigo)
        self.assertEqual(resultado["banco"], "341")
        self.assertAlmostEqual(resultado["valor"], 123.45, places=2)


if __name__ == "__main__":
    unittest.main()
