from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
import os
import logging

logger = logging.getLogger(__name__)

# ─── Configuração MongoDB ────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_MAX_POOL = int(os.getenv("MONGO_MAX_POOL", 300))  # nº máx. de conexões simultâneas que podem
MONGO_MIN_POOL = int(os.getenv("MONGO_MIN_POOL", 0))    # nº  mín. de conexões que o driver mantém sempre abertas no pool
MONGO_WAIT_QUEUE_TIMEOUT_MS = int(os.getenv("MONGO_WAIT_QUEUE_TIMEOUT_MS", 30_000))  # tempo limite (ms) que uma coroutine espera na fila quando o pool lota antes de lançar erro(30 segundos).
MONGO_MAX_CONNECTING = int(os.getenv("MONGO_MAX_CONNECTING", 10))    # nº máx. de conexões que podem estar sendo abertas ao mesmo tempo.
MONGO_MAX_IDLE_MS = int(os.getenv("MONGO_MAX_IDLE_MS", 300_000))    # quanto tempo uma conexão pode ficar ociosa antes de encerrar(5 minuto).
MONGO_SERVER_SELECTION_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", 10_000))   # quanto tempo (ms) o driver tenta encontrar um servidor elegível antes de desistir(10 segndos).
MONGO_CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", 10_000))   # tempo limite (ms) para estabelecer o socket TCP com o servidor, diz quanto tempo o driver espera para criar esse canal antes de desistir e declarar o servidor indisponível.(10 segundos).

# ─── Cliente com pool configurado ────────────
client = AsyncIOMotorClient(
    MONGO_URI,
    maxPoolSize=MONGO_MAX_POOL,
    minPoolSize=MONGO_MIN_POOL,
    waitQueueTimeoutMS=MONGO_WAIT_QUEUE_TIMEOUT_MS,
    maxConnecting=MONGO_MAX_CONNECTING,
    maxIdleTimeMS=MONGO_MAX_IDLE_MS,
    serverSelectionTimeoutMS=MONGO_SERVER_SELECTION_MS,
    connectTimeoutMS=MONGO_CONNECT_TIMEOUT_MS,
)

db = client["Reinf"]

# Mapeamento evento → coleção
_COLLECTIONS = {
    "R2010": "R2010",
    "R4010": "R4010",
    "R4020": "R4020"
}

# Configuração para o nome dos campos de acordo com cada payload.
EVENT_CONFIG = {
    "R2010": {
        "id_field":      "numDocto",
        "pessoa_fields": ["cnpjPrestador"],
    },
    "R4010": {
        "id_field":      "NumDoc",
        "pessoa_fields": ["cpfBenef", "cnpjBenef"],
    },
    "R4020": {
        "id_field":      "NumDoc",
        "pessoa_fields": ["cpfBenef", "cnpjBenef"],
    },
}


def get_collection(tipo_evento: str):
    """
        Converte o código do evento (ex: "R4010") no objeto collection correspondente.
    """
    colecao = _COLLECTIONS.get(tipo_evento)
    if not colecao:
        raise ValueError(f"Evento desconhecido: {tipo_evento}")
    return db[colecao]


def build_id(payload: dict, client_cnpj: str) -> str:
    """
       Monta _id no formato:
       <id_evento>-<nrInscEstab>-<cpfOuCnpjDoBeneficiario>-<client_cnpj>
    """
    # Identifica o evento
    tipo = payload["TpEvento"]

    cfg = EVENT_CONFIG.get(tipo)
    if cfg is None:
        raise ValueError(f"Evento '{tipo}' não configurado em EVENT_CONFIG")

    numdoc = payload[cfg["id_field"]]
    estab_cnpj = payload["nrInscEstab"]

    # Pega o cnpj ou cpf do Prestador/Beneficiario.
    pessoa_id = ""
    for fld in cfg["pessoa_fields"]:
        if fld in payload:
            pessoa_id = payload[fld]
            break

    return f"{numdoc}-{estab_cnpj}-{pessoa_id}-{client_cnpj}"


async def save_if_valid(resultado: dict, payload: dict, client_cnpj: str):
    """
    Insere no Mongo apenas se resultado['status']=='valido'.
    Ignora DuplicateKeyError para chaves já existentes.
    """
    if resultado.get("status") != "valido":
        return None

    idx = build_id(payload, client_cnpj)
    doc = {**payload, **resultado, "_id": idx}
    col = get_collection(payload["TpEvento"])

    try:
        result = await col.insert_one(doc)
        logger.info(f"[Mongo] Inserido {payload['TpEvento']} com _id={idx}")
        return result.inserted_id

    except DuplicateKeyError:
        logger.warning(f"[Mongo] Registro {idx} já existe, Ignorando...")
        return None
