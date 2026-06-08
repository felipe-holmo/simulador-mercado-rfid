# Mock do emulador RFID

Substituto do `rfid (1).exe` para desenvolvimento em macOS.

## Por que existe

O `.exe` original e um servidor HTTP escrito em Rust (axum + tokio), compilado
para Windows x86-64. No macOS Apple Silicon precisariamos de Wine, que esta
sendo descontinuado pelo Homebrew em 2026-09-01 e exige dependencias grandes
(gstreamer ~190MB) com instalacao via sudo interativo.

Este mock replica o comportamento observavel do binario para que voce possa
desenvolver e testar o codigo do trabalho. **Na maquina do professor, basta
trocar a URL do mock pela URL do `.exe` real — o codigo cliente nao muda.**

## Como rodar

```bash
python3 rfid_mock.py
# ou customizando:
python3 rfid_mock.py --host 127.0.0.1 --port 3000 --seed 42
```

Sem dependencias externas (so stdlib do Python 3).

## API

| Metodo | Path    | Resposta                                       |
|--------|---------|------------------------------------------------|
| GET    | /tags   | `{"tags": ["123456789012", ...]}` (HTTP 200)   |
| GET    | qualquer outro | `{"error":"not found"}` (HTTP 404)       |

### Exemplo de resposta

```json
{"tags": ["123456789012","065040302010","112233445566","112233445566","987654321098"]}
```

Cada chamada retorna uma **leitura RFID simulada**: um subconjunto das 10 tags
hardcoded, com:
- **Falhas:** ~20% de chance de uma tag nao aparecer (perda de leitura).
- **Duplicatas:** ~15% de chance de uma tag aparecer mais de uma vez.
- **Ordem:** aleatoria (simula ordem de deteccao nao-deterministica).

Ajuste `PROB_FALHA` e `PROB_DUPLICATA` em `rfid_mock.py` se quiser testar
casos extremos.

## Tags hardcoded (extraidas do binario)

```
123456789012
987654321098
112233445566
778899001122
554433221100
667788990011
102030405060
065040302010
999988887777
111122223333
```

Total: **10 codigos de 12 digitos**.

## Por que multiplas leituras sao necessarias

Em uma unica leitura, voce tipicamente perde 1-3 tags e ganha 0-3 duplicatas.
Fazendo a uniao de 3-5 leituras consecutivas, a probabilidade de reconstruir
o inventario completo (10 tags unicas) chega a ~99%.

Demonstracao com 5 leituras consecutivas:

```
Leitura 1: 9 tags totais, 8 unicas, 1 duplicata, 2 faltando
Leitura 2: 12 tags totais, 10 unicas, 2 duplicatas, 0 faltando
Leitura 3: 10 tags totais, 9 unicas, 1 duplicata, 1 faltando
Leitura 4: 9 tags totais, 7 unicas, 2 duplicatas, 3 faltando
Leitura 5: 9 tags totais, 9 unicas, 0 duplicatas, 1 faltando

Uniao das 5: 10 tags unicas (inventario completo reconstruido)
```

## Transicao para o .exe real

Quando o professor rodar o `rfid (1).exe` no Windows, ele vai imprimir algo como:

```
Server running at http://127.0.0.1:<porta>
```

No seu codigo cliente, basta:
1. Ajustar a `BASE_URL` para o endereco mostrado pelo `.exe`.
2. Continuar fazendo `GET /tags`.

Estrutura JSON e comportamento devem ser identicos (foi o que extraimos via
analise estatica do binario). Se houver divergencia minima, ajuste fino sera
local — sua arquitetura de reconciliacao continua valida.
