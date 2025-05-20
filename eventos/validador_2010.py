import logging
from pydantic import BaseModel, StrictInt, field_validator, model_validator
from typing import Literal
from datetime import date
from dicionarios import tp_servico
from utils.validadores_em_comum import validar_cnpj, validar_cno, limpar_numeros

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Evt2010(BaseModel):
    """
      Representa o evento R2010 da EFD‑Reinf, que detalha retenções de INSS,
      CPRB e demais informações relacionadas a serviços tomados.
     """

    TpEvento: Literal["R2010"]
    nrInsc: str
    indObra: Literal[0, 1, 2]
    nrInscEstab: str
    cnpjPrestador: str
    indCPRB: Literal[0, 1]

    numDocto: StrictInt
    serie: int
    dtEmissaoNF: date

    vlrBruto: float
    tpServico: int
    vlrBaseRet: float
    vlrRetencao: float

    @field_validator("cnpjPrestador")
    def validar_cnpj_prestador(cls, v):
        """
        Valida que 'cnpjPrestador' seja um CNPJ válido com 14 dígitos.
        """
        logger.debug(f"[field_validator] Validando cnpjPrestador: {v}")
        cnpj_digits = limpar_numeros(v)
        validar_cnpj(cnpj_digits)
        return cnpj_digits

    @model_validator(mode="after")
    def validar_nrinscestab_e_indobra(cls, model):
        """
        Valida o campo nrInscEstab de acordo com o valor de indObra:
          - Se indObra == 0, nrInscEstab deve ser um CNPJ (14 dígitos).
          - Se indObra == 1 ou 2, nrInscEstab deve ser um CNO (12 dígitos).
        """
        logger.debug(
            f"[model_validator 'after'] Validando nrInscEstab e indObra: "
            f"indObra={model.indObra}, nrInscEstab={model.nrInscEstab}"
        )
        nr_insc_estab = limpar_numeros(model.nrInscEstab)

        if model.indObra == 0:
            validar_cnpj(nr_insc_estab)
        else:
            validar_cno(nr_insc_estab)
        model.nrInscEstab = nr_insc_estab
        return model

    @model_validator(mode="after")
    def check_vlr_base_ret(self):
        """
        Valida que 'vlrBaseRet' não seja maior que 'vlrBruto'.
        """
        logger.debug(
            f"[model_validator 'after'] Validando vlrBaseRet <= vlrBruto: "
            f"vlrBaseRet={self.vlrBaseRet}, vlrBruto={self.vlrBruto}"
        )
        if self.vlrBaseRet is not None and self.vlrBruto is not None:
            if self.vlrBaseRet > self.vlrBruto:
                raise ValueError("vlrBaseRet não pode ser maior que vlrBruto.")
        return self

    @field_validator("tpServico", mode="before")
    def validar_tp_servico(cls, v):
        """
          Valida que 'tpServico' seja um código de serviço válido.

          Verifica se o valor informado está entre os valores definidos
          em tp_servico.TpServicoEnum. Se não estiver, lança ValueError.
        """
        validos = list(tp_servico.TpServicoEnum.values())
        if v not in validos:
            raise ValueError(
                f"Valor inválido para tpServico: {v}. Deve ser um dos: {validos}"
            )
        return v

    @model_validator(mode="after")
    def validar_vlr_retencao(cls, model):
        """
        Valida que, quando indCPRB == 0, o valor de vlrRetencao seja 11% de vlrBaseRet,
        permitindo uma pequena variação de centavos.
        """
        logger.debug(
            f"[model_validator 'after'] Validando vlrRetencao: "
            f"indCPRB={model.indCPRB}, vlrBaseRet={model.vlrBaseRet}, vlrRetencao={model.vlrRetencao}"
        )
        if model.indCPRB == 0:
            vlr_retencao_calculado = model.vlrBaseRet * 0.11
            tolerancia = 0.01  # Margem de tolerância

            if not (vlr_retencao_calculado - tolerancia <= model.vlrRetencao <= vlr_retencao_calculado + tolerancia):
                raise ValueError(
                    f"vlrRetencao deve ser 11% de vlrBaseRet (calculado: {vlr_retencao_calculado:.2f}), "
                    f"mas o valor fornecido foi {model.vlrRetencao:.2f}. Tolerância permitida: ±{tolerancia:.2f}."
                )
        elif model.indCPRB == 1:
            vlr_retencao_calculado = model.vlrBaseRet * 0.035
            tolerancia = 0.01  # Margem de tolerância

            if not (vlr_retencao_calculado - tolerancia <= model.vlrRetencao <= vlr_retencao_calculado + tolerancia):
                raise ValueError(
                    f"vlrRetencao deve ser 3,5% de vlrBaseRet (calculado: {vlr_retencao_calculado:.2f}), "
                    f"mas o valor fornecido foi {model.vlrRetencao:.2f}. Tolerância permitida: ±{tolerancia:.2f}."
                )

        return model

    @model_validator(mode="after")
    def validar_nrinsc(cls, model):
        """
        Valida o campo nrInsc:
          - Se indObra == 0, nrInsc deve ser um CNPJ (14 dígitos) ou os 8 primeiros dígitos devem bater com nrInscEstab.
        """
        logger.debug(
            f"[model_validator 'after'] Validando nrInsc e indObra: "
            f"indObra={model.indObra}, nrInsc={model.nrInsc}, nrInscEstab={model.nrInscEstab}"
        )

        if model.indObra == 0:
            # Se indObra for 0, valida nrInsc como CNPJ (14 dígitos) ou 8 primeiros dígitos
            nr_insc = limpar_numeros(model.nrInsc)
            nr_insc_estab = limpar_numeros(model.nrInscEstab)

            if len(nr_insc) == 14:
                # Se for CNPJ completo, valida o CNPJ
                validar_cnpj(nr_insc)
                model.nrInsc = nr_insc
            elif len(nr_insc) == 8:
                # Se for apenas os 8 primeiros dígitos, valida se batem com os 8 primeiros de nrInscEstab
                if nr_insc_estab[:8] != nr_insc:
                    raise ValueError(
                        f"O nrInsc ({nr_insc}) não corresponde ao nrInscEstab ({nr_insc_estab[:8]})."
                    )
                validar_cnpj(nr_insc_estab)
                model.nrInsc = nr_insc_estab
            else:
                raise ValueError("nrInsc deve ser um CNPJ com 14 dígitos ou os 8 primeiros dígitos de um CNPJ.")

        return model

    @model_validator(mode="after")
    def validar_vlr_base_sem_imposto(cls, model):
        """
        Valida que quando não houver valor de imposto (vlrRetencao), não deve haver base de cálculo (vlrBaseRet).
        """
        logger.debug(
            f"[model_validator 'after'] Validando vlrBaseRet quando não há vlrRetencao: "
            f"vlrBaseRet={model.vlrBaseRet}, vlrRetencao={model.vlrRetencao}"
        )

        if model.vlrRetencao == 0 or model.vlrRetencao is None:
            if model.vlrBaseRet > 0:
                raise ValueError(
                    "Quando não houver valor de imposto (vlrRetencao), não pode haver base de cálculo (vlrBaseRet).")
        # Se o valor de vlrRetencao for maior que 0, então a base de cálculo deve ser maior que 0.
        elif model.vlrRetencao > 0:
            if model.vlrBaseRet <= 0:
                raise ValueError(
                    "Quando houver valor de imposto (vlrRetencao > 0), deve haver base de cálculo (vlrBaseRet > 0).")

        return model
