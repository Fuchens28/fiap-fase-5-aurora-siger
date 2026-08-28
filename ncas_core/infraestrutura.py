"""Construção e resumo da infraestrutura local do NCAS."""

from __future__ import annotations

from .modelos import ModuleStatus, Modulo, RedeInfraestrutura


def build_aurora_colony() -> RedeInfraestrutura:
    """Cria uma rede local, determinística e independente do SIGIC."""
    dados_modulos = [
        ("CTL", "Centro de Controle", 1, 15.0),
        ("PWR", "Complexo de Energia", 1, 27.0),
        ("LSS", "Sistema de Suporte de Vida", 1, 505.0),
        ("HAB", "Complexo Habitacional", 2, 85.0),
        ("MED", "Complexo Medico", 2, 106.0),
        ("COM", "Sistema de Comunicacao", 3, 45.0),
        ("AGR", "Complexo de Agricultura", 3, 63.0),
        ("LOG", "Complexo de Logistica", 4, 50.0),
        ("MIN", "Complexo de Mineracao", 4, 93.0),
        ("RES", "Centro de Pesquisa", 5, 41.0),
    ]
    rede = RedeInfraestrutura(
        modules={
            modulo_id: Modulo(modulo_id, nome, prioridade, consumo)
            for modulo_id, nome, prioridade, consumo in dados_modulos
        },
        dependencies={
            "LSS": ("PWR",),
            "HAB": ("PWR", "LSS"),
            "MED": ("PWR", "LSS"),
            "COM": ("PWR",),
            "AGR": ("PWR", "LSS"),
            "LOG": ("PWR", "COM"),
            "MIN": ("PWR", "COM"),
            "RES": ("PWR", "COM"),
        },
    )
    return rede


def resumo_rede(rede: RedeInfraestrutura) -> dict[str, int | float]:
    """Calcula indicadores estruturados da infraestrutura."""
    modulos = list(rede.modules.values())
    return {
        "total_modulos": len(modulos),
        "modulos_ativos": sum(
            modulo.status == ModuleStatus.OPERATIONAL for modulo in modulos
        ),
        "modulos_criticos": sum(modulo.priority <= 2 for modulo in modulos),
        "consumo_nominal_kw": round(
            sum(modulo.energy_consumption_kw for modulo in modulos), 2
        ),
        "total_dependencias": sum(
            len(dependencias) for dependencias in rede.dependencies.values()
        ),
    }


def impacto_falha(rede: RedeInfraestrutura, modulo_id: str) -> list[str]:
    """Retorna o módulo e todos os módulos afetados por sua falha."""
    if modulo_id not in rede.modules:
        return []

    afetados = {modulo_id}
    mudou = True
    while mudou:
        mudou = False
        for dependente, dependencias in rede.dependencies.items():
            if dependente not in afetados and any(
                dependencia in afetados for dependencia in dependencias
            ):
                afetados.add(dependente)
                mudou = True
    return sorted(afetados)


def aplicar_cenario(rede: RedeInfraestrutura, cenario: str) -> str | None:
    """Aplica um cenário demonstrativo e retorna o módulo alterado."""
    cenarios = {
        "1": ("LSS", ModuleStatus.SHUTDOWN, "Falha crítica no suporte de vida"),
        "2": ("COM", ModuleStatus.DEGRADED, "Degradação do sistema de comunicação"),
        "3": ("PWR", ModuleStatus.SHUTDOWN, "Falha no complexo de energia"),
        "4": ("LOG", ModuleStatus.DEGRADED, "Falha não crítica na logística"),
    }
    dados = cenarios.get(cenario)
    if dados is None:
        return None
    modulo_id, status, _ = dados
    rede.modules[modulo_id].status = status
    return modulo_id


def listar_cenarios() -> list[tuple[str, str]]:
    """Retorna os cenários prontos para demonstração."""
    return [
        ("1", "Falha crítica no suporte de vida (LSS)"),
        ("2", "Degradação do sistema de comunicação (COM)"),
        ("3", "Falha no complexo de energia (PWR)"),
        ("4", "Falha não crítica na logística (LOG)"),
    ]
