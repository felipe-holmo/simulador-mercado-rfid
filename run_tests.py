#!/usr/bin/env python3
"""Runner de testes didatico do projeto.

Roda toda a suite de `unittest` da pasta `tests/`, mas em vez da saida
enxuta padrao (`....` ou `OK`), imprime um log bem detalhado no terminal:
para cada teste mostra o que ele verifica, o resultado e, em caso de
falha, o motivo completo. A ideia e que qualquer colega de grupo consiga
rodar e entender o que esta sendo testado sem ler o codigo.

Uso (a partir da raiz do projeto):

    python3 run_tests.py            # log completo
    python3 run_tests.py --quieto   # so o resumo no final
    NO_COLOR=1 python3 run_tests.py # sem cores ANSI

Nao precisa instalar nada: usa apenas a biblioteca padrao.
"""

import os
import sys
import time
import unittest


# --- Cores ANSI (desligam sozinhas se a saida nao for um terminal) -------

def _cores_ativas():
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


_USA_COR = _cores_ativas()


def _c(texto, codigo):
    if not _USA_COR:
        return texto
    return f"\033[{codigo}m{texto}\033[0m"


def verde(t):    return _c(t, "32")
def vermelho(t): return _c(t, "31")
def amarelo(t):  return _c(t, "33")
def azul(t):     return _c(t, "36")
def cinza(t):    return _c(t, "90")
def negrito(t):  return _c(t, "1")


LARGURA = 78
LINHA = cinza("-" * LARGURA)
LINHA_DUPLA = "=" * LARGURA


# --- Descricoes legiveis -------------------------------------------------

def descricao_do_teste(teste):
    """Texto explicando o que o teste faz.

    Usa a docstring do metodo de teste, se houver. Senao, transforma o
    nome do metodo (test_carrega_10_produtos) em uma frase legivel
    (carrega 10 produtos).
    """
    doc = teste.shortDescription()
    if doc:
        return doc
    nome = teste._testMethodName  # ex: test_lookup_por_ean_existente
    if nome.startswith("test_"):
        nome = nome[len("test_"):]
    return nome.replace("_", " ")


def nome_modulo(teste):
    return type(teste).__module__


def nome_classe(teste):
    return type(teste).__name__


# --- Resultado customizado que faz o log --------------------------------

class ResultadoVerboso(unittest.TestResult):
    """Coleta os resultados e imprime um log detalhado durante a execucao."""

    def __init__(self, total, quieto=False):
        super().__init__()
        self.total = total
        self.quieto = quieto
        self.indice = 0
        self._inicio_teste = None
        self._classe_atual = None
        self._teste_atual = None

    # -- ajuda interna --

    def _imprime_cabecalho_grupo(self, teste):
        classe = f"{nome_modulo(teste)}.{nome_classe(teste)}"
        if classe != self._classe_atual:
            self._classe_atual = classe
            print()
            print(azul(negrito(f">> Grupo: {classe}")))
            doc = (type(teste).__doc__ or "").strip().splitlines()
            if doc:
                print(cinza(f"   {doc[0]}"))

    def _prefixo(self):
        return cinza(f"[{self.indice:>2}/{self.total}]")

    # -- callbacks do unittest --

    def startTest(self, teste):
        super().startTest(teste)
        self.indice += 1
        self._teste_atual = teste
        self._inicio_teste = time.perf_counter()
        if self.quieto:
            return
        self._imprime_cabecalho_grupo(teste)
        print()
        print(f"{self._prefixo()} {negrito(teste._testMethodName)}")
        print(f"        o que testa: {descricao_do_teste(teste)}")

    def _duracao(self):
        if self._inicio_teste is None:
            return 0.0
        return time.perf_counter() - self._inicio_teste

    def addSuccess(self, teste):
        super().addSuccess(teste)
        if self.quieto:
            return
        print(f"        resultado:   {verde('PASSOU')} "
              f"{cinza(f'({self._duracao():.3f}s)')}")

    def addFailure(self, teste, err):
        super().addFailure(teste, err)
        if self.quieto:
            return
        print(f"        resultado:   {vermelho('FALHOU')} "
              f"{cinza(f'({self._duracao():.3f}s)')}")
        self._imprime_detalhe(err)

    def addError(self, teste, err):
        super().addError(teste, err)
        if self.quieto:
            return
        print(f"        resultado:   {vermelho('ERRO')} "
              f"{cinza(f'({self._duracao():.3f}s)')}")
        self._imprime_detalhe(err)

    def addSkip(self, teste, motivo):
        super().addSkip(teste, motivo)
        if self.quieto:
            return
        print(f"        resultado:   {amarelo('IGNORADO')} "
              f"{cinza(f'-> {motivo}')}")

    def _imprime_detalhe(self, err):
        texto = self._exc_info_to_string(err, self._teste_atual)
        print(vermelho("        detalhe da falha:"))
        for linha in texto.rstrip().splitlines():
            print(vermelho(f"          | {linha}"))


# --- Orquestracao --------------------------------------------------------

def coletar_testes(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from coletar_testes(item)
        else:
            yield item


def main():
    quieto = "--quieto" in sys.argv or "-q" in sys.argv

    raiz = os.path.dirname(os.path.abspath(__file__))
    os.chdir(raiz)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)

    print(LINHA_DUPLA)
    print(negrito("  SUITE DE TESTES"))
    print(cinza("  Cada teste abaixo verifica uma parte do sistema."))
    print(cinza("  PASSOU = comportamento esperado. FALHOU/ERRO = algo quebrou."))
    print(LINHA_DUPLA)

    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    testes = list(coletar_testes(suite))
    total = len(testes)

    if total == 0:
        print(vermelho("\nNenhum teste encontrado em tests/."))
        return 1

    resultado = ResultadoVerboso(total, quieto=quieto)

    inicio = time.perf_counter()
    suite.run(resultado)
    duracao = time.perf_counter() - inicio

    # -- Resumo final --
    print()
    print(LINHA)
    print(negrito("  RESUMO"))
    print(LINHA)
    falhas = len(resultado.failures)
    erros = len(resultado.errors)
    ignorados = len(resultado.skipped)
    passou = total - falhas - erros - ignorados

    print(f"  Total de testes : {total}")
    print(f"  {verde('Passaram')}        : {passou}")
    if falhas:
        print(f"  {vermelho('Falharam')}        : {falhas}")
    if erros:
        print(f"  {vermelho('Com erro')}        : {erros}")
    if ignorados:
        print(f"  {amarelo('Ignorados')}       : {ignorados}")
    print(f"  Tempo total     : {duracao:.3f}s")
    print(LINHA)

    if falhas or erros:
        print(vermelho(negrito("\n  >> A SUITE NAO PASSOU. Veja os detalhes acima.\n")))
        return 1

    print(verde(negrito("\n  >> TUDO CERTO! Todos os testes passaram.\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
