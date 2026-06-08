"""Carrega catalog.json e expoe lookups O(1)."""

from pathlib import Path
import json

CATALOG_PATH = Path(__file__).parent.parent / "data" / "catalog.json"


def carregar(path=CATALOG_PATH):
    """Retorna a lista de produtos lida do JSON do catalogo."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def indices(catalogo):
    """Retorna (por_rfid, por_ean) — dois dicts para lookup O(1).

    A ordem (por_rfid, por_ean) e contratual: bin/caixa.py desempacota
    nesta ordem. Nao inverter.
    """
    por_rfid = {produto["rfid"]: produto for produto in catalogo}
    por_ean = {produto["ean13"]: produto for produto in catalogo}
    return por_rfid, por_ean


def por_rfid(catalogo, rfid):
    """Retorna o produto com o RFID informado ou None."""
    for produto in catalogo:
        if produto["rfid"] == rfid:
            return produto
    return None


def por_ean(catalogo, ean):
    """Retorna o produto com o EAN-13 informado ou None."""
    for produto in catalogo:
        if produto["ean13"] == ean:
            return produto
    return None
