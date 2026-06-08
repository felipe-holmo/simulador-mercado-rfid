"""Parse e validacao de codigos FEBRABAN (boletos).

Suporta dois formatos:
- Codigo de barras: 44 digitos. O DV geral fica na posicao 5 e usa Mod 11
  (com regras especiais para resto 0, 1 e 10). Por essa complexidade e por
  estar fora do escopo do HANDOFF (que pede `validar_dv_mod10` para a linha
  de 47), o codigo de 44 digitos e aceito apenas por tamanho, sem validacao
  de DV. Ver nota no relatorio da sessao.
- Linha digitavel: 47 digitos, com 3 campos validados por Mod 10.
"""


def _calcular_dv_mod10(digitos: str) -> int:
    """Calcula o DV Mod 10 (FEBRABAN) de uma sequencia de digitos.

    Algoritmo:
      1. Multiplica os digitos da direita para a esquerda alternando
         pesos 2, 1, 2, 1, ...
      2. Se o produto for > 9, soma seus algarismos (ex: 14 -> 1 + 4 = 5).
      3. Soma todos os produtos.
      4. DV = (10 - (soma mod 10)) mod 10 (assim DV 10 vira 0).
    """
    soma = 0
    peso = 2
    for caractere in reversed(digitos):
        produto = int(caractere) * peso
        if produto > 9:
            produto = (produto // 10) + (produto % 10)
        soma += produto
        peso = 1 if peso == 2 else 2
    return (10 - (soma % 10)) % 10


def validar_dv_mod10(linha_digitavel: str) -> bool:
    """Valida o DV de cada um dos 3 campos da linha digitavel (47 digitos).

    Estrutura da linha digitavel (indices 0-based):
      - Campo 1: dados em [0:9],  DV no indice 9
      - Campo 2: dados em [10:20], DV no indice 20
      - Campo 3: dados em [21:31], DV no indice 31
    Retorna True somente se os 3 DVs conferirem.
    """
    if len(linha_digitavel) != 47 or not linha_digitavel.isdigit():
        return False
    campos = (
        (linha_digitavel[0:9], linha_digitavel[9]),
        (linha_digitavel[10:20], linha_digitavel[20]),
        (linha_digitavel[21:31], linha_digitavel[31]),
    )
    for dados, dv in campos:
        if _calcular_dv_mod10(dados) != int(dv):
            return False
    return True


def extrair_valor(codigo: str) -> float:
    """Extrai o valor do boleto, em reais.

    Posicoes do valor (em centavos), indices 0-based:
      - 44 digitos: codigo[9:19] (10 digitos, apos banco/moeda/dv/fator_venc)
      - 47 digitos: codigo[37:47] (10 digitos)
    Retorna o valor em reais (centavos / 100).
    """
    if len(codigo) == 44:
        centavos = int(codigo[9:19])
    elif len(codigo) == 47:
        centavos = int(codigo[37:47])
    else:
        raise ValueError(f"Tamanho invalido para extrair valor: {len(codigo)}")
    return centavos / 100


def parse(codigo: str) -> dict:
    """Faz o parse de um codigo FEBRABAN (boleto).

    Aceita 44 digitos (codigo de barras) ou 47 digitos (linha digitavel).
    Para 47 digitos valida o DV Mod 10 dos 3 campos; para 44 digitos aceita
    apenas por tamanho (DV Mod 11 nao validado, ver docstring do modulo).
    Retorna:
      {"tipo": "boleto",
       "banco": "341",
       "valor": 123.45,
       "codigo_original": "..."}
    Levanta ValueError se o tamanho for invalido ou o DV Mod 10 nao conferir.
    """
    if not isinstance(codigo, str) or not codigo.isdigit():
        raise ValueError("Codigo deve conter apenas digitos")
    if len(codigo) not in (44, 47):
        raise ValueError(f"Tamanho invalido: esperado 44 ou 47, recebido {len(codigo)}")
    if len(codigo) == 47 and not validar_dv_mod10(codigo):
        raise ValueError("DV Mod 10 invalido na linha digitavel")
    return {
        "tipo": "boleto",
        "banco": codigo[:3],
        "valor": extrair_valor(codigo),
        "codigo_original": codigo,
    }
