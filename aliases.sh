#!/usr/bin/env sh
# Atalhos para uso manual do simulador de mercado.
#
# COMO USAR — carregue uma vez por terminal (de qualquer diretorio):
#     source aliases.sh
#
# Para carregar automaticamente em todo terminal novo, adicione ao ~/.zshrc:
#     source "/Users/heitor.caldas/Documents/trabalho-kama/aliases.sh"
#
# Depois use os comandos curtos (veja todos com `ajuda`):
#     rfid.exe                                   # sobe o leitor RFID falso (mock)
#     recebimento --nf data/nf/nf_001_normal.json
#     caixa                                      # abre o caixa (interativo)
#     testes                                     # roda a suite de testes

# Descobre a raiz do projeto a partir da localizacao deste arquivo
# (idioma compativel com bash e zsh).
_kama_src="${BASH_SOURCE[0]:-${(%):-%x}}"
KAMA_ROOT="$(cd "$(dirname "$_kama_src")" >/dev/null 2>&1 && pwd)"

# Escolhe o interpretador: python3 (macOS/Linux) ou python (Windows).
if command -v python3 >/dev/null 2>&1; then
  _kama_py="python3"
else
  _kama_py="python"
fi

# --- Comandos principais ---------------------------------------------------
alias caixa="$_kama_py \"$KAMA_ROOT/bin/caixa.py\""
alias recebimento="$_kama_py \"$KAMA_ROOT/bin/recebimento.py\""
alias rfid.exe="$_kama_py \"$KAMA_ROOT/mock-server/rfid_mock.py\""
alias mock="$_kama_py \"$KAMA_ROOT/mock-server/rfid_mock.py\""
alias testes="$_kama_py \"$KAMA_ROOT/run_tests.py\""

# --- Cenarios prontos de recebimento (NF por caminho absoluto) -------------
# Funcionam de qualquer diretorio; exigem o leitor (rfid.exe) rodando.
alias receber-normal="$_kama_py \"$KAMA_ROOT/bin/recebimento.py\" --nf \"$KAMA_ROOT/data/nf/nf_001_normal.json\""
alias receber-falta="$_kama_py \"$KAMA_ROOT/bin/recebimento.py\" --nf \"$KAMA_ROOT/data/nf/nf_002_com_falta.json\""
alias receber-sobra="$_kama_py \"$KAMA_ROOT/bin/recebimento.py\" --nf \"$KAMA_ROOT/data/nf/nf_003_com_sobra.json\""

# --- Ajuda -----------------------------------------------------------------
ajuda() {
  cat <<EOF
Comandos do simulador de mercado (raiz: $KAMA_ROOT):

  rfid.exe / mock     Sobe o leitor RFID falso. Deixe rodando numa janela.
                      (aceita --port N e --seed N)
  recebimento --nf X  Concilia a leitura RFID contra a NF X e atualiza o estoque.
                      (aceita --reset-estoque e --rfid-url URL)
  receber-normal      Atalho: recebimento com a NF 001 (cenario OK).
  receber-falta       Atalho: recebimento com a NF 002 (cenario com falta).
  receber-sobra       Atalho: recebimento com a NF 003 (cenario com sobra).
  caixa               Abre o caixa (interativo). Use --arquivo X p/ modo batch.
  testes              Roda a suite de testes com log detalhado.
  ajuda               Mostra esta lista.

Fluxo tipico de demonstracao:
  1) rfid.exe          (janela 1 - deixe rodando)
  2) receber-normal    (janela 2 - abastece o estoque)
  3) caixa             (janela 2 - vende e da baixa no estoque)
EOF
}
