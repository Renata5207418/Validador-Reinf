from fastapi import FastAPI, HTTPException, Request, Depends, Header
from starlette.middleware.cors import CORSMiddleware
from pymongo.errors import DuplicateKeyError
from logging_config import configure_logging
from starlette.middleware import Middleware
from eventos.validador_4020 import Evt4020
from eventos.validador_2010 import Evt2010
from eventos.validador_4010 import Evt4010
from jwt.exceptions import PyJWTError
from pydantic import ValidationError
from database import save_if_valid
import logging
import jwt
import os


# Logger para este módulo
logger = logging.getLogger(__name__)

configure_logging(
    log_dir="logs",
    audit_filename="audit.log",
    error_filename="errors.log",
    backup_count=30,
    log_level="INFO",
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuração do FastAPI e CORS
# ─────────────────────────────────────────────────────────────────────────────

# noinspection PyTypeChecker
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )
]

app = FastAPI(
    title="API de Validação EFD‑Reinf",
    version="1.0",
    description="Endpoints para validar eventos R4020, R2010 e R4010",
    middleware=middleware,
)


@app.get("/health", tags=["Health"])
async def health_check():
    """
        Verificação da API, se está rodando.
    """
    return {"status": "ok"}


def get_client_cnpj_from_jwt(authorization: str = Header(..., description="Bearer <token JWT>")) -> str:
    """
        Extrai e valida o JWT do header, retorna o claim 'cnpj'
    """
    logger.debug("Auth header recebido: %s", authorization)

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header deve começar com 'Bearer '")
    token = authorization.split(" ", 1)[1]

    try:
        secret = os.getenv("JWT_SECRET")
        logger.debug("Usando secret=%s", secret)
        decoded = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        logger.debug("Token decodificado: %s", decoded)
    except PyJWTError:
        raise HTTPException(401, "Falha ao decodificar JWT")

    cnpj = decoded.get("cnpj")
    if not cnpj:
        raise HTTPException(400, "Campo 'cnpj' não encontrado no JWT")
    return cnpj


@app.post("/validar", tags=["Validação Única"])
async def validar_evento(request: Request, client_cnpj: str = Depends(get_client_cnpj_from_jwt)):
    """
    Rota que identifica e valida o evento EFD‑Reinf.
    Espera um JSON com a chave "evento" para determinar o tipo.
    """
    body = await request.json()
    tipo_evento = body.get("TpEvento")

    if not tipo_evento:
        mensagem = "Campo 'TpEvento' não encontrado no JSON."
        logger.error(mensagem)
        raise HTTPException(status_code=400, detail=mensagem)

    logger.info(f"Recebido evento {tipo_evento} para validação.")

    try:
        if tipo_evento == "R4020":
            Evt4020(**body)
        elif tipo_evento == "R2010":
            Evt2010(**body)
        elif tipo_evento == "R4010":
            Evt4010(**body)
        else:
            mensagem = f"Evento '{tipo_evento}' não reconhecido."
            logger.warning(mensagem)
            raise HTTPException(status_code=400, detail=mensagem)

    except ValidationError as e:
        logger.error(f"Evento {tipo_evento} contém erros de validação:")
        mensagens = []

        for err in e.errors():
            campo = "geral" if not err["loc"] else " -> ".join(str(loc) for loc in err["loc"])
            mensagem = f"Campo: {campo} | Erro: {err['msg']}"
            logger.error(f"    {mensagem}")
            mensagens.append(mensagem)

        raise HTTPException(status_code=422, detail=mensagens)

    resposta = {
        "evento": tipo_evento,
        "status": "valido",
        "mensagem": f"Evento {tipo_evento} validado com sucesso!"
    }

    try:
        await save_if_valid(resposta, body, client_cnpj)

    except DuplicateKeyError:
        logger.warning(f"Evento {tipo_evento} com _id duplicado, retornando 409")
        raise HTTPException(
            status_code=409,
            detail=f"Evento {tipo_evento} com mesma chave já existe"
        )
    return resposta


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000,  workers=4, log_level=os.getenv("LOG_LEVEL", "info"))
