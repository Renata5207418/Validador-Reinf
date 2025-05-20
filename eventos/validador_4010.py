import logging
from pydantic import BaseModel, StrictInt, field_validator, model_validator
from typing import Literal
from datetime import date
from dicionarios import nat_rend_pf
from utils.validadores_em_comum import validar_cnpj, limpar_numeros, validar_cpf

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Evt4010(BaseModel):
    """
    Representa o evento R4010 da EFD‑Reinf, destinado a informar rendimentos de pessoas físicas
    e os respectivos valores tributáveis e de imposto retido.
    """

    TpEvento: Literal["R4010"]
    nrInscEstab: str
    cpfBenef: str
    NumDoc: StrictInt
    natRend: int
    dtFG: date
    vlrRendBruto: float
    vlrRendTrib: float
    vlrIR: float

    @model_validator(mode="after")
    def validar_nrinscestab(cls, model):
        """
        Limpa e valida o CNPJ do estabelecimento.
        """
        logger.debug(
            f"[model_validator 'after'] Validando nrInscEstab e indObra: "
            f"nrInscEstab={model.nrInscEstab}"
        )
        nr_insc_estab = limpar_numeros(model.nrInscEstab)
        validar_cnpj(nr_insc_estab)
        model.nrInscEstab = nr_insc_estab

        return model

    @field_validator("cpfBenef")
    def validar_cpf_benef(cls, v):
        """
        Valida que 'cpfBenef' seja um CPF válido com 11 dígitos.
        """
        logger.debug(f"[field_validator] Validando cpfBenef: {v}")
        cpf = limpar_numeros(v)
        validar_cpf(cpf)
        return cpf

    @field_validator("natRend", mode="before")
    def validar_nat_rend(cls, v):
        """
        Valida a natureza do rendimento de pessoa física.
        Garante que v esteja entre os valores definidos em nat_rend_pf.NatRendEnum.
        """
        validos = list(nat_rend_pf.NatRendEnum.values())
        if v not in validos:
            raise ValueError(
                f"Valor inválido para NatRend: {v}."
                f" Conferir tabela Natureza de Rendimentos Anexo I dos leiautes da EFD-Reinf"
            )
        return v

    @model_validator(mode="after")
    def validar_valores_tributaveis(cls, model):
        """
        Valida os valores tributáveis e de imposto:

        1. vlrRendTrib ≤ vlrRendBruto
        2. Se vlrRendTrib = 0, então vlrIR = 0.
        3. Se vlrRendTrib > 0, então vlrIR > 0 e vlrIR ≤ vlrRendTrib.
        """
        # 1) vlrRendTrib <= vlrRendBruto
        if model.vlrRendTrib > model.vlrRendBruto:
            raise ValueError("vlrRendTrib não pode ser maior que vlrRendBruto.")

        # 2) se base tributável = 0, não pode ter imposto
        if model.vlrRendTrib == 0:
            if model.vlrIR > 0:
                raise ValueError(
                    "Quando não houver valor tributável (vlrRendTrib = 0), "
                    "não pode haver imposto (vlrIR > 0)."
                )
        else:
            # se base > 0, imposto deve > 0
            if model.vlrIR <= 0:
                raise ValueError(
                    "Quando houver valor tributável (vlrRendTrib > 0), "
                    "deve haver imposto (vlrIR > 0)."
                )
            # imposto não pode exceder base
            if model.vlrIR > model.vlrRendTrib:
                raise ValueError(
                    "O valor do imposto (vlrIR) não pode ser maior que "
                    "a base tributável (vlrRendTrib)."
                )

        return model
