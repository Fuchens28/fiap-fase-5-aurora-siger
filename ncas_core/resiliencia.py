"""Indicadores simples de resiliência operacional e energética."""

from __future__ import annotations

from .infraestrutura import impacto_falha
from .modelos import RedeInfraestrutura


def avaliar_resiliencia(rede: RedeInfraestrutura, modulo_id: str) -> dict[str, object]:
    """Calcula impacto, consumo comprometido e protocolo de recuperação."""
    modulo = rede.modules.get(modulo_id)
    impacto = impacto_falha(rede, modulo_id)
    consumo = sum(rede.modules[item].energy_consumption_kw for item in impacto)
    if modulo is None:
        return {
            "nivel": "DESCONHECIDO",
            "impacto": [],
            "consumo_comprometido_kw": 0.0,
            "acao_preventiva": "Nenhuma: módulo não encontrado.",
            "acao_recuperacao": "Verificar o identificador informado.",
        }
    if modulo.priority == 1:
        nivel = "CRITICO"
        recuperacao = "Ativar contingência, preservar serviços essenciais e iniciar recuperação imediata."
    elif len(impacto) > 2:
        nivel = "ALTO"
        recuperacao = "Isolar o módulo, avaliar dependências e iniciar manutenção prioritária."
    else:
        nivel = "MODERADO"
        recuperacao = "Registrar a ocorrência e programar manutenção operacional."
    return {
        "nivel": nivel,
        "impacto": impacto,
        "consumo_comprometido_kw": round(consumo, 2),
        "acao_preventiva": "Manter monitoramento, redundância e revisão humana do protocolo.",
        "acao_recuperacao": recuperacao,
    }
