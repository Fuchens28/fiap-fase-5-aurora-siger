"""Regras de álgebra booleana usadas nas decisões do NCAS."""

from __future__ import annotations

from typing import Any


class MotorLogico:
    """Aplica, explica e demonstra a regra de alerta da colônia."""

    @staticmethod
    def calcular_alerta(falha: bool, critico: bool) -> bool:
        """Calcula ALERTA = (FALHA AND CRITICO) OR (FALHA AND NOT CRITICO)."""
        return (falha and critico) or (falha and not critico)

    @staticmethod
    def calcular_emergencia(falha: bool, critico: bool) -> bool:
        """Indica emergência somente quando a falha afeta item crítico."""
        return falha and critico

    @staticmethod
    def tabela_verdade() -> list[dict[str, bool]]:
        """Retorna as quatro combinações possíveis da regra."""
        return [
            {
                "FALHA": falha,
                "CRITICO": critico,
                "ALERTA": MotorLogico.calcular_alerta(falha, critico),
            }
            for falha in (False, True)
            for critico in (False, True)
        ]

    @staticmethod
    def explicar_regra() -> str:
        """Apresenta a simplificação por distributividade e De Morgan."""
        return (
            "Regra original:\n"
            "  ALERTA = (FALHA AND CRITICO) OR (FALHA AND NOT CRITICO)\n\n"
            "Pela distributividade:\n"
            "  ALERTA = FALHA AND (CRITICO OR NOT CRITICO)\n\n"
            "Pelo complemento (X OR NOT X = VERDADEIRO):\n"
            "  ALERTA = FALHA AND VERDADEIRO\n"
            "  ALERTA = FALHA\n\n"
            "Confirmacao com De Morgan:\n"
            "  VERDADEIRO = NOT(CRITICO AND NOT CRITICO)\n"
            "  VERDADEIRO = (NOT CRITICO) OR CRITICO\n"
            "Logo, qualquer falha gera ALERTA, independentemente de CRITICO."
        )
