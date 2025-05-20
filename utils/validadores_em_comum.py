import logging

"""
Coleção de funções de validação e limpeza:
 - validar_cnpj, validar_cno, validar_cpf
 - limpar_numeros
 - cálculo de dígitos verificadores de CNPJ
"""


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def calcular_dv_cnpj(cnpj_parcial: str) -> str:
    """Retorna os 2 dígitos verificadores de um CNPJ base (12 dígitos)."""
    logger.debug(f"Calculando DVs para CNPJ base de 12 dígitos: {cnpj_parcial}")

    def _dv(cnpj_part, pesos):
        soma = sum(int(d) * p for d, p in zip(cnpj_part, pesos))
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)

    dv1 = _dv(cnpj_parcial, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    dv2 = _dv(cnpj_parcial + dv1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    logger.debug(f"dv1={dv1}, dv2={dv2} (CNPJ)")
    return dv1 + dv2


def validar_cnpj(cnpj_digits: str) -> None:
    """Checa se o CNPJ tem 14 dígitos e dígitos verificadores corretos."""
    logger.debug(f"Validando CNPJ: {cnpj_digits}")
    if len(cnpj_digits) != 14:
        raise ValueError("CNPJ deve conter 14 dígitos numéricos.")

    base = cnpj_digits[:12]
    dv_esperado = calcular_dv_cnpj(base)
    dv_informado = cnpj_digits[-2:]
    logger.debug(f"dv_esperado={dv_esperado}, dv_informado={dv_informado}")
    if dv_informado != dv_esperado:
        raise ValueError(
            f"CNPJ inválido: dígitos verificadores incorretos "
            f"(Esperado={dv_esperado}, Recebido={dv_informado})."
        )


def validar_cno(cno_digits: str) -> None:
    """
    Checa se o CNO tem 12 dígitos numéricos.
    """
    logger.debug(f"Validando CNO: {cno_digits}")
    if len(cno_digits) != 12:
        raise ValueError("CNO deve conter 12 dígitos numéricos.")


def validar_cpf(cpf: str) -> None:
    """
    Valida um CPF: deve ter 11 dígitos, não ser uma sequência repetida
    e ter dígitos verificadores corretos.
    """
    cpf = limpar_numeros(cpf)
    if len(cpf) != 11:
        raise ValueError("CPF deve conter 11 dígitos numéricos.")

    if cpf == cpf[0] * 11:
        raise ValueError("CPF inválido: sequência repetida.")

    def calc_dv(digs: str, peso_inicial: int) -> str:
        soma = sum(int(d) * p for d, p in zip(digs, range(peso_inicial, 1, -1)))
        resto = soma * 10 % 11
        return '0' if resto == 10 else str(resto)

    dv1 = calc_dv(cpf[:9], 10)
    dv2 = calc_dv(cpf[:9] + dv1, 11)
    if cpf[-2:] != dv1 + dv2:
        raise ValueError(f"CPF inválido: dígitos verificadores incorretos (esperado {dv1+dv2}).")

    logger.debug(f"CPF {cpf} validado com sucesso.")


def limpar_numeros(valor: str) -> str:
    """
    Remove todos os caracteres não numéricos da string.
    """
    return ''.join(filter(str.isdigit, valor))
