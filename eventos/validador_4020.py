import logging
from pydantic import BaseModel, StrictInt, field_validator, model_validator
from typing import Literal
from datetime import date
from dicionarios import nat_rend_pj
from utils.validadores_em_comum import validar_cnpj, limpar_numeros

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Evt4020(BaseModel):
    """
     Representa o evento R4020 da EFD‑Reinf, para informar retenções de IR e agregados
     sobre pagamentos a pessoas jurídicas.
     """

    TpEvento: Literal["R4020"]
    nrInscEstab: str
    cnpjBenef: str
    NumDoc: StrictInt
    natRend: int
    dtFG: date
    vlrBruto: float
    vlrBaseIR: float
    vlrIR: float
    vlrBaseAgreg: float
    vlrAgreg: float

    @field_validator("cnpjBenef")
    def validar_cnpj_benef(cls, v):
        """
        Valida que 'cnpjPrestador' seja um CNPJ válido com 14 dígitos.
        """
        logger.debug(f"[field_validator] Validando cnpjBenef: {v}")
        cnpj_digits = limpar_numeros(v)
        validar_cnpj(cnpj_digits)
        return cnpj_digits

    @model_validator(mode="after")
    def validar_nrinscestab(cls, model):
        """
        Valida o campo nrInscEstab.
        """
        logger.debug(
            f"[model_validator 'after'] Validando nrInscEstab e indObra: "
            f"nrInscEstab={model.nrInscEstab}"
        )
        nr_insc_estab = limpar_numeros(model.nrInscEstab)
        validar_cnpj(nr_insc_estab)
        model.nrInscEstab = nr_insc_estab
        return model

    @model_validator(mode="after")
    def validar_vlrbase_vlr(cls, model):
        """
        Valida que:
        - Se houver base de cálculo, o imposto deve ser maior que 0.
        - Se houver imposto, a base de cálculo deve ser maior que 0.
        - O valor do imposto não pode ser maior que o valor da base de cálculo.
        - A única situação onde 0 é aceito é quando ambos os campos (base e imposto) forem 0.
        """
        # O valor das bases não pode ser maior que o valor brutno
        if model.vlrBaseIR > model.vlrBruto:
            raise ValueError("vlrBaseIR não pode ser maior que vlrBruto.")
        if model.vlrBaseAgreg > model.vlrBruto:
            raise ValueError("vlrBaseAgreg não pode ser maior que vlrBruto.")

        def validar_par(valor_base, valor_imposto, nome_base, nome_imposto):
            if valor_base is None or valor_base == 0:
                if valor_imposto > 0:
                    raise ValueError(
                        f"Quando não houver valor de {nome_base} (valor = 0),"
                        f" não pode haver valor em {nome_imposto} (> 0)."
                    )
            else:
                if valor_imposto <= 0:
                    raise ValueError(
                        f"Quando houver valor de {nome_base} (> 0), deve haver valor em {nome_imposto} (> 0)."
                    )
                if valor_imposto > valor_base:
                    raise ValueError(
                        f"O valor de {nome_imposto} não pode ser maior que o da {nome_base}."
                    )

        validar_par(model.vlrBaseIR, model.vlrIR, "vlrBaseIR", "vlrIR")
        validar_par(model.vlrBaseAgreg, model.vlrAgreg, "vlrBaseAgreg", "vlrAgreg")

        return model

    @field_validator("natRend", mode="before")
    def validar_nat_rend(cls, v):
        """
         Valida a natureza do rendimento.
         - Garante que o código esteja entre os valores definidos em nat_rend_pj.NatRendEnum.
        """
        validos = list(nat_rend_pj.NatRendEnum.values())
        if v not in validos:
            raise ValueError(
                f"Valor inválido para NatRend: {v}."
                f" Conferir tabela Natureza de Rendimentos Anexo I dos leiautes da EFD-Reinf"
            )
        return v
