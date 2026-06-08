"""
Mock do emulador RFID (rfid.exe) escrito em Python.

Objetivo: replicar o comportamento observado no binario Rust original
(axum + tokio) para permitir desenvolvimento do trabalho em macOS,
onde nao podemos rodar o .exe nativamente.

Comportamento simulado:
- Endpoint: GET /tags
- Resposta: JSON {"tags": [...]} com codigos de 12 digitos
- 10 codigos hardcoded (extraidos do binario)
- Falhas: cada tag pode nao aparecer em uma leitura (Bernoulli)
- Duplicatas: cada tag pode aparecer mais de uma vez (Bernoulli)
- Ordem: aleatoria, simulando ordem de detecao do leitor real

Para trocar pelo .exe real:
- Basta apontar o cliente para a URL/porta do .exe (que tambem expoe /tags).
- O codigo de processamento nao muda.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import random
import sys
import argparse


# Codigos extraidos do binario rfid.exe (strings de 12 digitos).
TAGS_HARDCODED = [
    "123456789012",
    "987654321098",
    "112233445566",
    "778899001122",
    "554433221100",
    "667788990011",
    "102030405060",
    "065040302010",
    "999988887777",
    "111122223333",
]


# Probabilidade de cada tag NAO aparecer na leitura (falha de leitura RFID).
# 0.20 = 20% de chance de perder cada tag => obriga multiplas leituras.
PROB_FALHA = 0.20

# Probabilidade de cada tag aparecer DUPLICADA.
# 0.15 = 15% de chance => obriga deduplica antes de contar.
PROB_DUPLICATA = 0.15


def gerar_leitura(tags_base):
    """Gera uma leitura simulada com falhas e duplicatas.

    Retorna uma lista (nao um set!) — duplicatas sao intencionais.
    """
    leitura = []
    for tag in tags_base:
        # Simula falha: pula a tag com prob_falha.
        if random.random() < PROB_FALHA:
            continue
        leitura.append(tag)
        # Simula duplicata: adiciona de novo com prob_duplicata.
        if random.random() < PROB_DUPLICATA:
            leitura.append(tag)
    # Embaralha para simular ordem de deteccao nao-deterministica.
    random.shuffle(leitura)
    return leitura


class RFIDHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/tags":
            tags = gerar_leitura(TAGS_HARDCODED)
            body = json.dumps({"tags": tags}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')

    def log_message(self, format, *args):
        # Log enxuto: so metodo + path + status.
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def main():
    parser = argparse.ArgumentParser(description="Mock do emulador RFID")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=3000, help="Porta (default: 3000)")
    parser.add_argument("--seed", type=int, default=None, help="Seed para reprodutibilidade")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    server = HTTPServer((args.host, args.port), RFIDHandler)
    print(f"Server running at http://{args.host}:{args.port}")
    print(f"Endpoint: GET http://{args.host}:{args.port}/tags")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
