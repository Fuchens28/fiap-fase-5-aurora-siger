"""Simulação local de estratégias de prompting."""

from __future__ import annotations

import json
from typing import Any


class SimuladorIA:
    """Produz respostas simuladas sem realizar chamadas externas."""

    @staticmethod
    def zero_shot(pergunta: str) -> str:
        """Gera uma resposta sem exemplos prévios."""
        return (
            f"[ZERO-SHOT]\nPergunta: {pergunta}\n"
            "Resposta simulada: analisar sensores, registros e nível de risco."
        )

    @staticmethod
    def few_shot() -> str:
        """Gera uma resposta após exemplos de entrada e saída."""
        return (
            "[FEW-SHOT]\n"
            "Exemplo 1: temperatura alta -> recomendar resfriamento.\n"
            "Exemplo 2: comunicacao interrompida -> recomendar diagnostico.\n"
            "Pergunta: radiação acima do limite -> ?\n"
            "Resposta simulada: isolar a área e verificar os sensores."
        )

    @staticmethod
    def saida_json() -> str:
        """Gera uma resposta que respeita um formato JSON."""
        resposta: dict[str, Any] = {
            "classificacao": "ATENCAO",
            "confianca": 0.92,
            "acao_recomendada": "Verificar o modulo de comunicacao",
            "origem": "simulacao_NCAS",
        }
        return "[SAIDA ESTRUTURADA EM JSON]\n" + json.dumps(
            resposta, ensure_ascii=False, indent=4
        )

    @staticmethod
    def recomendacao_diagnostico(
        modulo_id: str,
        nome_modulo: str,
        prioridade: int,
        status: str,
        impacto: list[str],
        contexto: str = "Nenhum protocolo relacionado foi encontrado.",
        resiliencia: str = "Não avaliada.",
    ) -> str:
        """Simula recomendação baseada nos dados do diagnóstico."""
        nivel = "crítico" if prioridade <= 2 else "operacional"
        acao = (
            "ativar o protocolo de contingência e preservar o suporte de vida"
            if prioridade == 1
            else "isolar o módulo, avaliar dependências e iniciar manutenção"
        )
        return (
            "[RECOMENDAÇÃO CONTEXTUAL]\n"
            f"Módulo: {modulo_id} - {nome_modulo}\n"
            f"Prioridade: P{prioridade} ({nivel}) | Status: {status}\n"
            f"Impacto previsto: {', '.join(impacto)}\n"
            f"Contexto recuperado: {contexto}\n"
            f"Resiliência: {resiliencia}\n"
            f"Ação simulada: {acao}."
        )
