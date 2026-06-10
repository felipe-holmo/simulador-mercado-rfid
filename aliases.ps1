# Atalhos PowerShell para uso manual do simulador de mercado (Windows).
#
# COMO USAR — carregue uma vez por terminal (na raiz do projeto):
#     . .\aliases.ps1
#   (note o ponto e o espaco no inicio: e o "dot-source" do PowerShell)
#
# Para carregar em todo terminal novo, adicione a mesma linha ao seu perfil.
# Descubra o caminho do perfil com:  echo $PROFILE
#
# Depois use os comandos curtos (veja todos com `ajuda`):
#     rfid.exe                                   # sobe o leitor RFID falso (mock)
#     recebimento --nf data\nf\nf_001_normal.json
#     caixa                                      # abre o caixa (interativo)

# Raiz do projeto (a partir da localizacao deste arquivo).
$KamaRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Interpretador: usa 'python' se existir, senao 'python3'.
if (Get-Command python -ErrorAction SilentlyContinue) {
  $script:KamaPy = "python"
} else {
  $script:KamaPy = "python3"
}

# --- Comandos principais ---------------------------------------------------
function caixa       { & $script:KamaPy "$KamaRoot\caixa.py" @args }
function recebimento { & $script:KamaPy "$KamaRoot\recebimento.py" @args }
function rfid.exe    { & $script:KamaPy "$KamaRoot\rfid_mock.py" @args }
function mock        { & $script:KamaPy "$KamaRoot\rfid_mock.py" @args }

# --- Cenarios prontos de recebimento (NF por caminho absoluto) -------------
# Funcionam de qualquer diretorio; exigem o leitor (rfid.exe) rodando.
function receber-normal { & $script:KamaPy "$KamaRoot\recebimento.py" --nf "$KamaRoot\data\nf\nf_001_normal.json" @args }
function receber-falta  { & $script:KamaPy "$KamaRoot\recebimento.py" --nf "$KamaRoot\data\nf\nf_002_com_falta.json" @args }
function receber-sobra  { & $script:KamaPy "$KamaRoot\recebimento.py" --nf "$KamaRoot\data\nf\nf_003_com_sobra.json" @args }

# --- Ajuda -----------------------------------------------------------------
function ajuda {
  Write-Host @"
Comandos do simulador de mercado (raiz: $KamaRoot):

  rfid.exe / mock     Sobe o leitor RFID falso. Deixe rodando numa janela.
                      (aceita --port N e --seed N)
  recebimento --nf X  Concilia a leitura RFID contra a NF X e atualiza o estoque.
                      (aceita --reset-estoque e --rfid-url URL)
  receber-normal      Atalho: recebimento com a NF 001 (cenario OK).
  receber-falta       Atalho: recebimento com a NF 002 (cenario com falta).
  receber-sobra       Atalho: recebimento com a NF 003 (cenario com sobra).
  caixa               Abre o caixa (interativo). Use --arquivo X p/ modo batch.
  ajuda               Mostra esta lista.

Fluxo tipico de demonstracao:
  1) rfid.exe          (janela 1 - deixe rodando)
  2) receber-normal    (janela 2 - abastece o estoque)
  3) caixa             (janela 2 - vende e da baixa no estoque)
"@
}
