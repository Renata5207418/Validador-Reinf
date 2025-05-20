import os
import logging
from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger.json import JsonFormatter


def configure_logging(
    log_dir: str = "logs",
    audit_filename: str = "audit.log",
    error_filename: str = "errors.log",
    backup_count: int = 30,
    log_level: str = "INFO"
):
    """
    Prepara o logger raiz para:
      - gravar logs INFO em `logs/audit.log` (rotaciona à meia-noite, guarda 30 dias)
      - gravar logs WARNING+ em `logs/errors.log` (idem)
      - usar formato JSON com timestamps e acentuação
    """

    # 1) garante que a pasta de logs exista
    os.makedirs(log_dir, exist_ok=True)

    # 2) cria o formatter JSON
    formatter = JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        json_ensure_ascii=False
    )

    # 3) handler de auditoria (só INFO)
    audit_path = os.path.join(log_dir, audit_filename)
    audit_handler = TimedRotatingFileHandler(
        filename=audit_path,
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding="utf-8"
    )
    audit_handler.setLevel(logging.INFO)
    # só deixa passar exatamente INFO
    audit_handler.addFilter(lambda record: record.levelno == logging.INFO)
    audit_handler.setFormatter(formatter)

    # 4) handler de erros (WARNING ou superior)
    error_path = os.path.join(log_dir, error_filename)
    error_handler = TimedRotatingFileHandler(
        filename=error_path,
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    # 5) configura o logger raiz
    root = logging.getLogger()
    root.setLevel(log_level.upper())
    root.addHandler(audit_handler)
    root.addHandler(error_handler)
