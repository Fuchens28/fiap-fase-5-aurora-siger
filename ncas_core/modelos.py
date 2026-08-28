"""Modelos de dados utilizados pelo NCAS."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModuleStatus(str, Enum):
    """Estados possíveis de um módulo da colônia."""

    OPERATIONAL = "OPERACIONAL"
    DEGRADED = "DEGRADADO"
    SURVIVAL = "SOBREVIVENCIA"
    SHUTDOWN = "DESLIGADO"

    def __str__(self) -> str:
        return self.value


@dataclass
class Modulo:
    """Módulo de infraestrutura analisado pelo NCAS."""

    module_id: str
    name: str
    priority: int
    energy_consumption_kw: float
    status: ModuleStatus = ModuleStatus.OPERATIONAL


@dataclass
class RedeInfraestrutura:
    """Conjunto de módulos que representa a infraestrutura da colônia."""

    modules: dict[str, Modulo]
    dependencies: dict[str, tuple[str, ...]]


@dataclass
class RegistroColonia:
    """Evento persistido nos arquivos do sistema."""

    id_registro: int
    data_hora: str
    categoria: str
    descricao: str
    falha: bool
    critico: bool
    modulo_id: str | None = None
    impacto: tuple[str, ...] = ()
    recomendacao: str = ""
    revisao_humana: str = "PENDENTE"
