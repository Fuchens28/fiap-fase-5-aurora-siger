"""Nucleo do sistema NCAS - Nucleo Cognitivo da Aurora Siger."""

from . import otimizacao
from .aplicacao import AplicacaoNCAS
from .conhecimento import BaseConhecimento
from .infraestrutura import build_aurora_colony, impacto_falha, resumo_rede
from .logica import MotorLogico
from .modelos import ModuleStatus, Modulo, RedeInfraestrutura, RegistroColonia
from .prompts import CatalogoPrompts, SimuladorIA
from .repositorio import RepositorioColonia
from .resiliencia import avaliar_resiliencia

__all__ = [
    "AplicacaoNCAS",
    "BaseConhecimento",
    "CatalogoPrompts",
    "ModuleStatus",
    "Modulo",
    "MotorLogico",
    "RedeInfraestrutura",
    "RegistroColonia",
    "RepositorioColonia",
    "SimuladorIA",
    "avaliar_resiliencia",
    "build_aurora_colony",
    "impacto_falha",
    "otimizacao",
    "resumo_rede",
]
