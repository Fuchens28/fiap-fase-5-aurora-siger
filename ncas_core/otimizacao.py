"""Otimizacao do indice de risco do NCAS.

Implementa, apenas com a biblioteca padrao, os conceitos do Capitulo 7:

- erro quadratico medio (MSE) como funcao de custo;
- gradiente descendente como algoritmo de ajuste dos parametros;
- regularizacao L2 (Ridge) para controlar a magnitude dos coeficientes.

O objetivo e didatico: mostrar que o indice de risco exibido pelo NCAS pode
ser ajustado a partir do historico da colonia, em vez de depender de pesos
escolhidos no chute. Nao ha treinamento de rede neural nem uso de bibliotecas
externas; o modelo e uma regressao linear de tres variaveis.

Modelo:
    risco = w0 + w1 . prioridade + w2 . modulos_impactados + w3 . consumo

As variaveis de entrada sao normalizadas para o intervalo [0, 1] antes do
ajuste, o que mantem o gradiente estavel com uma taxa de aprendizado fixa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

# Historico didatico de ocorrencias ja avaliadas por operadores humanos.
# Cada tupla e (prioridade, modulos_impactados, consumo_kw, risco_observado).
# O risco observado e a nota de 0 a 1 que a equipe atribuiu ao incidente.
HISTORICO_OCORRENCIAS: list[tuple[int, int, float, float]] = [
    (1, 4, 759.0, 0.98),
    (1, 9, 1030.0, 1.00),
    (1, 6, 214.0, 0.90),
    (2, 1, 85.0, 0.55),
    (2, 1, 106.0, 0.58),
    (3, 4, 229.0, 0.62),
    (3, 1, 63.0, 0.40),
    (4, 1, 50.0, 0.25),
    (4, 1, 93.0, 0.30),
    (5, 1, 41.0, 0.15),
]

# Limites usados na normalizacao das variaveis de entrada.
PRIORIDADE_MAXIMA = 5
MODULOS_MAXIMO = 10
CONSUMO_MAXIMO_KW = 1030.0


@dataclass
class ResultadoTreino:
    """Resultado de um ajuste por gradiente descendente."""

    pesos: list[float] = field(default_factory=list)
    mse_inicial: float = 0.0
    mse_final: float = 0.0
    epocas: int = 0
    taxa_aprendizado: float = 0.0
    regularizacao: float = 0.0

    @property
    def reducao_percentual(self) -> float:
        """Percentual de reducao do erro entre o inicio e o fim do treino."""
        if self.mse_inicial == 0:
            return 0.0
        return (self.mse_inicial - self.mse_final) / self.mse_inicial * 100


def normalizar(prioridade: int, modulos: int, consumo: float) -> list[float]:
    """Converte uma ocorrencia em variaveis normalizadas entre 0 e 1.

    A prioridade e invertida porque P1 e o caso mais grave: o modelo precisa
    de um valor alto quando a prioridade e alta.
    """
    prioridade_invertida = (PRIORIDADE_MAXIMA - prioridade) / (PRIORIDADE_MAXIMA - 1)
    proporcao_modulos = modulos / MODULOS_MAXIMO
    proporcao_consumo = min(consumo / CONSUMO_MAXIMO_KW, 1.0)
    return [1.0, prioridade_invertida, proporcao_modulos, proporcao_consumo]


def prever(pesos: list[float], entradas: list[float]) -> float:
    """Calcula a previsao do modelo linear para uma ocorrencia."""
    return sum(peso * entrada for peso, entrada in zip(pesos, entradas))


def erro_quadratico_medio(
    pesos: list[float],
    amostras: list[tuple[list[float], float]],
) -> float:
    """Calcula o MSE = (1/n) . somatorio (y_real - y_previsto)^2.

    O erro e elevado ao quadrado para evitar que desvios positivos e
    negativos se cancelem e para penalizar mais os desvios grandes.
    """
    if not amostras:
        return 0.0
    total = 0.0
    for entradas, observado in amostras:
        desvio = observado - prever(pesos, entradas)
        total += desvio * desvio
    return total / len(amostras)


def preparar_amostras(
    historico: list[tuple[int, int, float, float]] | None = None,
) -> list[tuple[list[float], float]]:
    """Transforma o historico bruto em pares (entradas normalizadas, alvo)."""
    dados = HISTORICO_OCORRENCIAS if historico is None else historico
    return [
        (normalizar(prioridade, modulos, consumo), risco)
        for prioridade, modulos, consumo, risco in dados
    ]


def treinar(
    historico: list[tuple[int, int, float, float]] | None = None,
    taxa_aprendizado: float = 0.2,
    epocas: int = 4000,
    regularizacao: float = 0.01,
) -> ResultadoTreino:
    """Ajusta os pesos do modelo por gradiente descendente.

    A cada epoca os pesos caminham na direcao oposta ao gradiente da funcao
    de custo, seguindo a regra de atualizacao do Capitulo 7:

        w := w - taxa . gradiente

    O termo de regularizacao L2 penaliza pesos de magnitude elevada, o que
    reduz a sensibilidade do modelo a variacoes do historico e evita que uma
    unica variavel domine a decisao (overfitting).

    A taxa de aprendizado precisa respeitar a condicao de estabilidade
    ``taxa . (2 . lambda) < 2``. Se ela for grande demais, o passo ultrapassa
    o ponto de minimo e o erro cresce a cada epoca em vez de diminuir. Por
    isso o laco interrompe o treino caso os pesos deixem de ser finitos.
    """
    amostras = preparar_amostras(historico)
    if not amostras:
        return ResultadoTreino()

    quantidade_pesos = len(amostras[0][0])
    pesos = [0.0] * quantidade_pesos
    pesos_anteriores = list(pesos)
    mse_inicial = erro_quadratico_medio(pesos, amostras)

    for _ in range(epocas):
        gradientes = [0.0] * quantidade_pesos
        for entradas, observado in amostras:
            desvio = prever(pesos, entradas) - observado
            for indice, entrada in enumerate(entradas):
                gradientes[indice] += 2 * desvio * entrada / len(amostras)
        # O peso w0 (intercepto) nao recebe penalizacao L2.
        for indice in range(1, quantidade_pesos):
            gradientes[indice] += 2 * regularizacao * pesos[indice]
        for indice in range(quantidade_pesos):
            pesos[indice] -= taxa_aprendizado * gradientes[indice]
        if not all(isfinite(peso) for peso in pesos):
            # Divergencia: a taxa de aprendizado e alta demais para este
            # lambda. Interrompe e devolve o ultimo estado estavel.
            pesos = list(pesos_anteriores)
            break
        pesos_anteriores = list(pesos)

    return ResultadoTreino(
        pesos=pesos,
        mse_inicial=mse_inicial,
        mse_final=erro_quadratico_medio(pesos, amostras),
        epocas=epocas,
        taxa_aprendizado=taxa_aprendizado,
        regularizacao=regularizacao,
    )


def prever_risco(
    resultado: ResultadoTreino,
    prioridade: int,
    modulos: int,
    consumo: float,
) -> float:
    """Estima o risco de uma ocorrencia nova, limitado ao intervalo [0, 1]."""
    if not resultado.pesos:
        return 0.0
    bruto = prever(resultado.pesos, normalizar(prioridade, modulos, consumo))
    return max(0.0, min(1.0, bruto))


def classificar_risco(risco: float) -> str:
    """Traduz o indice numerico em uma faixa legivel pelo operador."""
    if risco >= 0.85:
        return "CRITICO"
    if risco >= 0.60:
        return "ALTO"
    if risco >= 0.35:
        return "MODERADO"
    return "BAIXO"


def comparar_regularizacao(
    valores: tuple[float, ...] = (0.0, 0.01, 0.1, 0.5, 1.0),
) -> list[tuple[float, float, float]]:
    """Compara o efeito de diferentes intensidades de regularizacao.

    Retorna tuplas (lambda, mse_final, soma_absoluta_dos_pesos). Quanto maior
    o lambda, menores os coeficientes e maior o erro no historico: e o
    compromisso entre vies e variancia discutido no Capitulo 7.
    """
    comparacao = []
    for valor in valores:
        resultado = treinar(regularizacao=valor)
        magnitude = sum(abs(peso) for peso in resultado.pesos[1:])
        comparacao.append((valor, resultado.mse_final, magnitude))
    return comparacao


def relatorio(resultado: ResultadoTreino) -> str:
    """Monta o relatorio textual exibido no menu do sistema."""
    if not resultado.pesos:
        return "Não há histórico suficiente para treinar o modelo."
    nomes = ["intercepto", "prioridade", "módulos impactados", "consumo"]
    linhas = [
        "[OTIMIZAÇÃO DO ÍNDICE DE RISCO]",
        f"Amostras do histórico: {len(HISTORICO_OCORRENCIAS)}",
        f"Taxa de aprendizado: {resultado.taxa_aprendizado}",
        f"Épocas: {resultado.epocas}",
        f"Regularização L2 (lambda): {resultado.regularizacao}",
        "",
        "Função de custo: erro quadrático médio (MSE)",
        f"  MSE inicial (pesos zerados): {resultado.mse_inicial:.6f}",
        f"  MSE final   (após o ajuste): {resultado.mse_final:.6f}",
        f"  Redução do erro: {resultado.reducao_percentual:.2f}%",
        "",
        "Pesos ajustados:",
    ]
    for nome, peso in zip(nomes, resultado.pesos):
        linhas.append(f"  w[{nome}] = {peso:+.4f}")
    linhas.append("")
    linhas.append("Efeito da regularização (lambda | MSE | soma dos pesos):")
    for valor, mse, magnitude in comparar_regularizacao():
        linhas.append(f"  {valor:<5} | {mse:.6f} | {magnitude:.4f}")
    linhas.append("")
    linhas.append(
        "Leitura: lambda maior reduz a magnitude dos pesos e aumenta o erro\n"
        "no histórico. O valor intermediário mantém o erro baixo sem deixar\n"
        "uma única variável dominar a decisão."
    )
    return "\n".join(linhas)
