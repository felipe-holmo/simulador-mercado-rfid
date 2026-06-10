"""
Mock do emulador RFID (rfid.exe) escrito em Python.

Objetivo: replicar o comportamento observado no binario Rust original
(axum + tokio) para permitir desenvolvimento do trabalho em macOS,
onde nao podemos rodar o .exe nativamente.

Comportamento simulado:
- Endpoint: GET /tags
- Resposta: JSON {"tags": [...]} com codigos de 12 digitos
- TAGS_HARDCODED representa as tags FISICAS presentes no leitor; o mesmo
  codigo pode aparecer multiplas vezes (varias unidades do mesmo produto).
  Por isso cada tag fisica e tratada de forma independente: na leitura
  podem sair varios eventos do mesmo codigo, um por unidade lida.
- Falhas: cada tag fisica pode nao aparecer em uma leitura (Bernoulli) —
  obriga multiplas leituras ate o max-merge convergir.
- Ordem: aleatoria, simulando ordem de detecao do leitor real.

Para trocar pelo .exe real:
- Basta apontar o cliente para a URL/porta do .exe (que tambem expoe /tags).
- O codigo de processamento nao muda.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import random
import sys
import argparse


# Tags FISICAS no leitor. Modelo real: cada tag fisica e uma unidade do
# produto. Tags com mesmo codigo (mesmo produto, multiplas unidades) sao
# representadas por entradas repetidas — assim como o rfid.exe original.
# Composicao: 3x cafe, 2x leite, 1x cada um dos demais => 13 tags fisicas,
# 10 codigos distintos.
TAGS_HARDCODED = [
    "123456789012",  # Cafe Pilao 500g (unidade 1/3)
    "123456789012",  # Cafe Pilao 500g (unidade 2/3)
    "123456789012",  # Cafe Pilao 500g (unidade 3/3)
    "987654321098",  # Leite Itambe 1L (unidade 1/2)
    "987654321098",  # Leite Itambe 1L (unidade 2/2)
    "112233445566",  # Arroz Tio Joao 5kg
    "778899001122",  # Feijao Camil 1kg
    "554433221100",  # Acucar Uniao 1kg
    "667788990011",  # Macarrao Galo 500g
    "102030405060",  # Oleo Liza 900ml
    "065040302010",  # Sal Cisne 1kg
    "999988887777",  # Farinha Dona Benta 1kg
    "111122223333",  # Molho Pomarola 340g
]


# Probabilidade de cada tag fisica NAO aparecer na leitura (falha Bernoulli).
# 0.20 = 20% de chance de perder cada tag => obriga multiplas leituras ate
# o max-merge convergir para a quantidade fisica real.
PROB_FALHA = 0.20


def gerar_leitura(tags_base):
    """Gera uma leitura simulada com falhas Bernoulli por tag fisica.

    Cada entrada em tags_base e uma tag fisica independente: pode falhar
    individualmente (modelo do rfid.exe real). Retorna lista preservando
    a ordem aleatoria de deteccao.
    """
    leitura = []
    for tag in tags_base:
        if random.random() < PROB_FALHA:
            continue
        leitura.append(tag)
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
