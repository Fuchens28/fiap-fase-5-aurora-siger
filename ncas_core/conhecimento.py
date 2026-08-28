"""Recuperação de contexto local para simular um fluxo RAG."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any


class BaseConhecimento:
    """Busca orientações relevantes em uma base JSON local."""

    def __init__(self, caminho: str | Path | None = None) -> None:
        self.caminho = Path(caminho) if caminho else Path(__file__).with_name("base_conhecimento.json")
        with self.caminho.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, list):
            raise ValueError("a base de conhecimento deve ser uma lista")
        self.documentos: list[dict[str, Any]] = dados

    def buscar(self, consulta: str, limite: int = 3) -> list[dict[str, Any]]:
        """Retorna documentos ordenados pela quantidade de palavras coincidentes."""
        palavras = self._normalizar(consulta).split()
        palavras = set(palavras)
        candidatos: list[tuple[int, dict[str, Any]]] = []
        for documento in self.documentos:
            chaves = {
                self._normalizar(str(chave))
                for chave in documento.get("palavras_chave", [])
            }
            pontuacao = len(palavras & chaves)
            if pontuacao:
                candidatos.append((pontuacao, documento))
        candidatos.sort(key=lambda item: item[0], reverse=True)
        return [documento for _, documento in candidatos[:limite]]

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Remove acentos para que a busca aceite variações de digitação."""
        decomposicao = unicodedata.normalize("NFD", texto.lower())
        return "".join(caractere for caractere in decomposicao if unicodedata.category(caractere) != "Mn")

    @staticmethod
    def formatar_contexto(documentos: list[dict[str, Any]]) -> str:
        """Transforma documentos recuperados em contexto para um prompt."""
        if not documentos:
            return "Nenhum protocolo relacionado foi encontrado."
        return "\n".join(
            f"- {documento['titulo']}: {documento['orientacao']}"
            for documento in documentos
        )
