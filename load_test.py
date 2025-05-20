from httpx import Limits, Timeout
import asyncio
import httpx
import jwt
import os
import time
import argparse
from itertools import cycle

# Templates para cada tipo de evento
TEMPLATES = {
    'R2010': {
        "TpEvento": "R2010",
        "nrInsc": "12287133",
        "indObra": 0,
        "nrInscEstab": "12287133000170",
        "cnpjPrestador": "10490181000135",
        "indCPRB": 0,
        "serie": 1,
        "dtEmissaoNF": "2025-04-10",
        "vlrBruto": 10529.35,
        "tpServico": 100000001,
        "vlrBaseRet": 100,
        "vlrRetencao": 11
    },
    'R4010': {
        "TpEvento": "R4010",
        "nrInscEstab": "09524519000143",
        "cpfBenef": "10551205997",
        "natRend": 13002,
        "dtFG": "2025-01-15",
        "vlrRendBruto": 1000,
        "vlrRendTrib": 100,
        "vlrIR": 10
    },
    'R4020': {
        "TpEvento": "R4020",
        "nrInscEstab": "12287133000170",
        "cnpjBenef": "49996377000131",
        "natRend": 12042,
        "dtFG": "2025-01-15",
        "vlrBruto": 200.0,
        "vlrBaseIR": 100,
        "vlrIR": 10,
        "vlrBaseAgreg": 100,
        "vlrAgreg": 100
    }
}


def generate_payload(event_type, idx):
    """Clone o template e define um número de documento único."""
    payload = TEMPLATES[event_type].copy()
    # Atribui numeração única por índice
    if event_type == 'R2010':
        payload['numDocto'] = 5000 + idx
    else:
        payload['NumDoc'] = (7000 if event_type == 'R4010' else 8000) + idx
    return payload


async def send_event(client, url, token, payload):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    return await client.post(url, json=payload, headers=headers)


async def run_load(count, concurrency):
    url = "http://127.0.0.1:8000/validar"
    print("Iniciando validação…")
    secret = os.getenv('JWT_SECRET', 'mysecret')
    token = jwt.encode({'cnpj': '09524519000143'}, secret, algorithm='HS256')

    start = time.time()
    limits = Limits(max_connections=concurrency, max_keepalive_connections=concurrency//2)
    timeout = Timeout(connect=10.0, read=30.0, write=30.0, pool=60.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        sem = asyncio.Semaphore(concurrency)
        event_cycle = cycle(['R2010', 'R4010', 'R4020'])

        async def bounded_send(i):
            async with sem:
                evt = next(event_cycle)
                payload = generate_payload(evt, i)
                try:
                    return await send_event(client, url, token, payload)
                except Exception:
                    return None

        tasks = [asyncio.create_task(bounded_send(i)) for i in range(count)]
        responses = await asyncio.gather(*tasks)

    duration = time.time() - start
    succ = sum(1 for r in responses if getattr(r, 'status_code', 0) == 200)
    fail = count - succ
    print(f"Total: {count} | Sucessos: {succ} | Falhas: {fail}")
    print(f"Tempo: {duration:.2f}s | {count/duration:.2f} req/s")


def main():
    parser = argparse.ArgumentParser(description="Load-test do Validador EFD-Reinf")
    parser.add_argument('--count', type=int, default=100,
                        help="Total de eventos a enviar")
    parser.add_argument('--concurrency', type=int, default=10,
                        help="Número de requisições paralelas")
    args = parser.parse_args()
    asyncio.run(run_load(args.count, args.concurrency))


if __name__ == "__main__":
    main()
