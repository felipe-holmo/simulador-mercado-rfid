"""Auto-detecta o tipo de codigo lido pelo caixa."""


def detectar(codigo: str) -> str:
    """Classifica o codigo lido em um dos 5 outcomes.

    Retorna:
      "produto"        se len(codigo) == 13 e isdigit
      "boleto_barra"   se len(codigo) == 44 e isdigit
      "boleto_linha"   se len(codigo) == 47 e isdigit
      "finalizar"      se codigo.upper() == "FIM"
      "invalido"       caso contrario
    """
    if codigo.upper() == "FIM":
        return "finalizar"
    if codigo.isdigit():
        if len(codigo) == 13:
            return "produto"
        if len(codigo) == 44:
            return "boleto_barra"
        if len(codigo) == 47:
            return "boleto_linha"
    return "invalido"
