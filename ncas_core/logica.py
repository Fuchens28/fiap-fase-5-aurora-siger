"""Regras de algebra booleana usadas nas decisoes do NCAS.

O sistema implementa duas regras logicas, cada uma simplificada por um
caminho diferente do Capitulo 2:

1. Regra de ALERTA, simplificada pelos teoremas de simplificacao
   (distributividade, complementaridade da soma e identidade do produto).
2. Regra de BLOQUEIO, simplificada pelo primeiro teorema de De Morgan.

Notacao usada nos comentarios: ``.`` para AND, ``+`` para OR e ``'`` para
NOT, seguindo a convencao do material da disciplina.
"""

from __future__ import annotations


class MotorLogico:
    """Aplica, explica e demonstra as regras de decisao da colonia."""

    @staticmethod
    def calcular_alerta(falha: bool, critico: bool) -> bool:
        """Calcula ALERTA = (FALHA . CRITICO) + (FALHA . CRITICO').

        A forma original e mantida no codigo de proposito, para que a
        equivalencia com a forma simplificada possa ser demonstrada.
        """
        return (falha and critico) or (falha and not critico)

    @staticmethod
    def calcular_alerta_simplificado(falha: bool, critico: bool) -> bool:
        """Calcula a forma reduzida ALERTA = FALHA.

        O parametro ``critico`` continua na assinatura apenas para permitir a
        comparacao direta com ``calcular_alerta`` na tabela-verdade.
        """
        return falha

    @staticmethod
    def calcular_emergencia(falha: bool, critico: bool) -> bool:
        """Indica emergencia somente quando a falha atinge um modulo critico.

        EMERGENCIA = FALHA . CRITICO
        """
        return falha and critico

    @staticmethod
    def tabela_verdade() -> list[dict[str, bool]]:
        """Compara a regra original e a simplificada nas quatro combinacoes."""
        return [
            {
                "FALHA": falha,
                "CRITICO": critico,
                "ALERTA_ORIGINAL": MotorLogico.calcular_alerta(falha, critico),
                "ALERTA_SIMPLIFICADO": MotorLogico.calcular_alerta_simplificado(
                    falha, critico
                ),
            }
            for falha in (False, True)
            for critico in (False, True)
        ]

    @staticmethod
    def explicar_regra() -> str:
        """Apresenta a simplificacao da regra de ALERTA passo a passo."""
        return (
            "REGRA 1 - ALERTA (teoremas de simplificação)\n"
            "\n"
            "Expressão original:\n"
            "  ALERTA = (FALHA . CRITICO) + (FALHA . CRITICO')\n"
            "\n"
            "Passo 1 - Distributividade do produto sobre a soma (Teorema 16):\n"
            "  A.B + A.C = A.(B + C)\n"
            "  ALERTA = FALHA . (CRITICO + CRITICO')\n"
            "\n"
            "Passo 2 - Complementaridade da soma (Teorema 4):\n"
            "  A + A' = 1\n"
            "  ALERTA = FALHA . 1\n"
            "\n"
            "Passo 3 - Identidade do produto (Teorema 5):\n"
            "  A . 1 = A\n"
            "  ALERTA = FALHA\n"
            "\n"
            "Por que o resultado se mantém: os dois termos originais cobrem\n"
            "os únicos valores possíveis de CRITICO. Se há falha, um dos dois\n"
            "termos é sempre verdadeiro, então CRITICO não altera a saída.\n"
            "A variável é redundante para o ALERTA e foi eliminada.\n"
            "\n"
            "CRITICO não foi descartado do sistema: ele continua decidindo a\n"
            "regra EMERGENCIA = FALHA . CRITICO, que aciona a contingência."
        )

    @staticmethod
    def calcular_acesso(autorizado: bool, modulo_ativo: bool) -> bool:
        """Libera a consulta apenas se ACESSO = AUTORIZADO . ATIVO."""
        return autorizado and modulo_ativo

    @staticmethod
    def calcular_bloqueio(autorizado: bool, modulo_ativo: bool) -> bool:
        """Calcula BLOQUEIO = (AUTORIZADO . ATIVO)'.

        Forma original: negacao do acesso liberado.
        """
        return not (autorizado and modulo_ativo)

    @staticmethod
    def calcular_bloqueio_simplificado(autorizado: bool, modulo_ativo: bool) -> bool:
        """Calcula BLOQUEIO = AUTORIZADO' + ATIVO', obtida por De Morgan.

        Esta e a forma usada na pratica: permite informar ao operador qual
        das duas condicoes causou o bloqueio, sem recalcular a expressao.
        """
        return (not autorizado) or (not modulo_ativo)

    @staticmethod
    def tabela_verdade_bloqueio() -> list[dict[str, bool]]:
        """Compara as duas formas da regra de BLOQUEIO."""
        return [
            {
                "AUTORIZADO": autorizado,
                "ATIVO": ativo,
                "BLOQUEIO_ORIGINAL": MotorLogico.calcular_bloqueio(autorizado, ativo),
                "BLOQUEIO_SIMPLIFICADO": MotorLogico.calcular_bloqueio_simplificado(
                    autorizado, ativo
                ),
            }
            for autorizado in (False, True)
            for ativo in (False, True)
        ]

    @staticmethod
    def explicar_bloqueio() -> str:
        """Apresenta a aplicacao do primeiro teorema de De Morgan."""
        return (
            "REGRA 2 - BLOQUEIO (primeiro teorema de De Morgan)\n"
            "\n"
            "Política de acesso da colônia:\n"
            "  Liberar a consulta apenas se o operador estiver AUTORIZADO\n"
            "  e o módulo estiver ATIVO.\n"
            "\n"
            "  ACESSO  = AUTORIZADO . ATIVO\n"
            "  BLOQUEIO = (AUTORIZADO . ATIVO)'\n"
            "\n"
            "Primeiro teorema de De Morgan:\n"
            "  (A . B)' = A' + B'\n"
            "\n"
            "Aplicando o teorema:\n"
            "  BLOQUEIO = AUTORIZADO' + ATIVO'\n"
            "\n"
            "Por que o resultado se mantém: negar uma condição conjunta\n"
            "equivale a exigir que ao menos uma das partes tenha falhado.\n"
            "As duas formas produzem a mesma saída nas quatro combinações.\n"
            "\n"
            "Ganho prático: a forma negada isola a causa. O sistema deixa de\n"
            "responder apenas 'bloqueado' e passa a indicar se o problema foi\n"
            "a falta de autorização, o módulo inativo, ou os dois."
        )

    @staticmethod
    def motivo_bloqueio(autorizado: bool, modulo_ativo: bool) -> str:
        """Usa a forma de De Morgan para explicar a causa do bloqueio."""
        motivos = []
        if not autorizado:
            motivos.append("operador não autorizado")
        if not modulo_ativo:
            motivos.append("módulo inativo")
        if not motivos:
            return "Acesso liberado: operador autorizado e módulo ativo."
        return "Acesso bloqueado: " + " e ".join(motivos) + "."
