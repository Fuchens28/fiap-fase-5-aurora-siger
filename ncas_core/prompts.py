"""Engenharia de prompts e simulacao local de IA generativa.

O NCAS nao realiza chamadas a APIs externas. Os prompts sao montados a partir
do catalogo ``prompts.json`` e as respostas sao simuladas, o que mantem a
demonstracao reproduzivel e sem dependencias.

Cada prompt do catalogo segue os quatro elementos de projeto apresentados no
Capitulo 5:

1. tarefa: o que o modelo deve fazer;
2. contexto: as informacoes que ele nao tem como adivinhar;
3. exemplos: como uma boa saida se parece (usados no few-shot);
4. formato de saida: a forma exata da resposta esperada.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CatalogoPrompts:
    """Carrega e renderiza os prompts estruturados do arquivo JSON."""

    def __init__(self, caminho: str | Path | None = None) -> None:
        self.caminho = (
            Path(caminho) if caminho else Path(__file__).with_name("prompts.json")
        )
        with open(self.caminho, "r", encoding="utf-8") as arquivo:
            documento = json.load(arquivo)
        if not isinstance(documento, dict) or "prompts" not in documento:
            raise ValueError("o catálogo de prompts deve conter a chave 'prompts'")
        self.versao: str = documento.get("versao", "0")
        self.prompts: list[dict[str, Any]] = documento["prompts"]

    def listar(self) -> list[tuple[str, str, str]]:
        """Retorna (id, titulo, tecnica) de cada prompt disponivel."""
        return [
            (prompt["id"], prompt["titulo"], prompt["tecnica"])
            for prompt in self.prompts
        ]

    def obter(self, id_prompt: str) -> dict[str, Any] | None:
        for prompt in self.prompts:
            if prompt["id"] == id_prompt:
                return prompt
        return None

    def por_tecnica(self, tecnica: str) -> dict[str, Any] | None:
        """Retorna o primeiro prompt de uma tecnica (zero-shot, few-shot...)."""
        for prompt in self.prompts:
            if prompt["tecnica"] == tecnica:
                return prompt
        return None

    def renderizar(self, id_prompt: str, **variaveis: str) -> str:
        """Monta o texto final do prompt substituindo as variaveis.

        As variaveis nao informadas viram um marcador explicito, para que o
        operador perceba o que ficou faltando em vez de enviar um prompt
        incompleto ao modelo.
        """
        prompt = self.obter(id_prompt)
        if prompt is None:
            raise ValueError(f"prompt '{id_prompt}' não encontrado")
        exemplos = "\n".join(prompt.get("exemplos", []))
        valores = {
            "contexto": prompt["contexto"],
            "tarefa": prompt["tarefa"],
            "formato_saida": prompt["formato_saida"],
            "exemplos": exemplos,
        }
        for nome in prompt.get("variaveis", []):
            valores[nome] = variaveis.get(nome, f"<{nome} não informado>")
        return prompt["template"].format(**valores)

    def descrever(self, id_prompt: str, **variaveis: str) -> str:
        """Exibe o prompt renderizado junto da resposta simulada."""
        prompt = self.obter(id_prompt)
        if prompt is None:
            raise ValueError(f"prompt '{id_prompt}' não encontrado")
        return (
            f"[{prompt['tecnica'].upper()}] {prompt['titulo']}\n"
            f"Objetivo: {prompt['objetivo']}\n"
            f"\n--- PROMPT ENVIADO ---\n"
            f"{self.renderizar(id_prompt, **variaveis)}\n"
            f"\n--- RESPOSTA SIMULADA ---\n"
            f"{prompt['resposta_simulada']}"
        )


class SimuladorIA:
    """Produz respostas simuladas sem realizar chamadas externas."""

    @staticmethod
    def zero_shot(pergunta: str) -> str:
        """Gera uma resposta sem exemplos previos no prompt."""
        return (
            f"[ZERO-SHOT]\nPergunta: {pergunta}\n"
            "Resposta simulada: analisar sensores, registros e nível de risco."
        )

    @staticmethod
    def few_shot() -> str:
        """Gera uma resposta apos exemplos de entrada e saida."""
        return (
            "[FEW-SHOT]\n"
            "Exemplo 1: temperatura alta -> recomendar resfriamento.\n"
            "Exemplo 2: comunicação interrompida -> recomendar diagnóstico.\n"
            "Pergunta: radiação acima do limite -> ?\n"
            "Resposta simulada: isolar a área e verificar os sensores."
        )

    @staticmethod
    def saida_json() -> str:
        """Gera uma resposta que respeita um contrato JSON."""
        resposta: dict[str, Any] = {
            "classificacao": "ATENCAO",
            "confianca": 0.92,
            "acao_recomendada": "Verificar o módulo de comunicação",
            "origem": "simulacao_NCAS",
        }
        return "[SAÍDA ESTRUTURADA EM JSON]\n" + json.dumps(
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
        risco: str = "Não estimado.",
    ) -> str:
        """Simula a recomendacao construida a partir dos dados do diagnostico."""
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
            f"Índice de risco estimado: {risco}\n"
            f"Ação simulada: {acao}."
        )
