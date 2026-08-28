"""Persistência robusta em texto e JSON."""

from __future__ import annotations

import csv
import json
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .infraestrutura import resumo_rede
from .modelos import ModuleStatus, RedeInfraestrutura, RegistroColonia


class RepositorioColonia:
    """Lê, valida e grava registros da colônia."""

    def __init__(
        self,
        arquivo_txt: str | Path = "registros_colonia.txt",
        arquivo_json: str | Path = "dados_colonia.json",
    ) -> None:
        self.arquivo_txt = Path(arquivo_txt)
        self.arquivo_json = Path(arquivo_json)
        self.registros: list[RegistroColonia] = []
        self.avisos_leitura: list[str] = []
        self.carregar_txt()

    def proximo_id(self) -> int:
        """Retorna o próximo identificador disponível."""
        return max((registro.id_registro for registro in self.registros), default=0) + 1

    def adicionar(self, registro: RegistroColonia) -> None:
        """Grava no texto e só depois confirma o registro em memória."""
        self.arquivo_txt.parent.mkdir(parents=True, exist_ok=True)
        with self.arquivo_txt.open("a", encoding="utf-8", newline="") as arquivo:
            escritor = csv.writer(arquivo, delimiter="|", lineterminator="\n")
            escritor.writerow(
                [
                    registro.id_registro,
                    registro.data_hora,
                    registro.categoria,
                    registro.descricao,
                    str(registro.falha),
                    str(registro.critico),
                ]
            )
        self.registros.append(registro)

    def consultar(self) -> list[RegistroColonia]:
        """Retorna uma cópia dos registros carregados."""
        return list(self.registros)

    def atualizar_revisao(self, id_registro: int, status: str) -> bool:
        """Atualiza a revisão humana de um registro existente."""
        status_normalizado = status.strip().upper()
        if status_normalizado not in {"PENDENTE", "APROVADA", "REJEITADA"}:
            raise ValueError("status de revisão inválido")
        for registro in self.registros:
            if registro.id_registro == id_registro:
                registro.revisao_humana = status_normalizado
                return True
        return False

    def carregar_txt(self) -> None:
        """Carrega linhas válidas e ignora linhas inválidas com aviso."""
        self.registros.clear()
        self.avisos_leitura.clear()
        if not self.arquivo_txt.exists():
            return
        with self.arquivo_txt.open("r", encoding="utf-8", newline="") as arquivo:
            leitor = csv.reader(arquivo, delimiter="|")
            for numero, partes in enumerate(leitor, start=1):
                if len(partes) != 6:
                    self.avisos_leitura.append(f"Linha {numero} ignorada: formato inválido.")
                    continue
                try:
                    falha = self._ler_booleano(partes[4])
                    critico = self._ler_booleano(partes[5])
                    self.registros.append(
                        RegistroColonia(
                            id_registro=int(partes[0].strip()),
                            data_hora=partes[1].strip(),
                            categoria=partes[2].strip(),
                            descricao=partes[3].strip(),
                            falha=falha,
                            critico=critico,
                        )
                    )
                except (ValueError, IndexError):
                    self.avisos_leitura.append(f"Linha {numero} ignorada: dados inválidos.")

    @staticmethod
    def _ler_booleano(valor: str) -> bool:
        valor_normalizado = valor.strip().lower()
        if valor_normalizado == "true":
            return True
        if valor_normalizado == "false":
            return False
        raise ValueError("valor booleano inválido")

    def salvar_json(self, rede: RedeInfraestrutura | None = None) -> None:
        """Salva JSON formatado usando substituição atômica."""
        documento: dict[str, Any] = {
            "sistema": "Nucleo Cognitivo da Aurora Siger (NCAS)",
            "atualizado_em": datetime.now().astimezone().isoformat(),
            "total_registros": len(self.registros),
            "registros": [asdict(registro) for registro in self.registros],
        }
        if rede is not None:
            documento["infraestrutura_ncas"] = resumo_rede(rede)

        self.arquivo_json.parent.mkdir(parents=True, exist_ok=True)
        temporario: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.arquivo_json.parent,
                prefix=f"{self.arquivo_json.stem}_",
                suffix=".tmp",
                delete=False,
            ) as arquivo:
                temporario = arquivo.name
                json.dump(documento, arquivo, ensure_ascii=False, indent=4)
                arquivo.write("\n")
            Path(temporario).replace(self.arquivo_json)
        finally:
            if temporario is not None and Path(temporario).exists():
                Path(temporario).unlink()

    def carregar_json(self) -> dict[str, Any] | None:
        """Valida e carrega o JSON salvo sem perder dados anteriores em caso de erro."""
        if not self.arquivo_json.exists():
            return None
        with self.arquivo_json.open("r", encoding="utf-8") as arquivo:
            documento = json.load(arquivo)
        if not isinstance(documento, dict):
            raise ValueError("o documento JSON deve ser um objeto")
        registros = documento.get("registros", [])
        if not isinstance(registros, list):
            raise ValueError("o campo registros deve ser uma lista")
        novos_registros = []
        campos_obrigatorios = {
            "id_registro",
            "data_hora",
            "categoria",
            "descricao",
            "falha",
            "critico",
        }
        campos_opcionais = {
            "modulo_id",
            "impacto",
            "recomendacao",
            "revisao_humana",
        }
        for numero, item in enumerate(registros, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"registro {numero} deve ser um objeto")
            if not campos_obrigatorios.issubset(item) or set(item) - (
                campos_obrigatorios | campos_opcionais
            ):
                raise ValueError(f"registro {numero} possui campos inválidos")
            if (
                not isinstance(item["id_registro"], int)
                or isinstance(item["id_registro"], bool)
                or not isinstance(item["data_hora"], str)
                or not isinstance(item["categoria"], str)
                or not isinstance(item["descricao"], str)
                or not isinstance(item["falha"], bool)
                or not isinstance(item["critico"], bool)
            ):
                raise ValueError(f"registro {numero} possui tipos inválidos")
            if "modulo_id" in item and item["modulo_id"] is not None and not isinstance(
                item["modulo_id"], str
            ):
                raise ValueError(f"registro {numero} possui tipos inválidos")
            if "impacto" in item and (
                not isinstance(item["impacto"], list)
                or not all(isinstance(modulo_id, str) for modulo_id in item["impacto"])
            ):
                raise ValueError(f"registro {numero} possui tipos inválidos")
            if "recomendacao" in item and not isinstance(item["recomendacao"], str):
                raise ValueError(f"registro {numero} possui tipos inválidos")
            if "revisao_humana" in item and not isinstance(item["revisao_humana"], str):
                raise ValueError(f"registro {numero} possui tipos inválidos")
            dados_registro = dict(item)
            if "impacto" in dados_registro:
                dados_registro["impacto"] = tuple(dados_registro["impacto"])
            novos_registros.append(RegistroColonia(**dados_registro))
        self.registros = novos_registros
        return documento
