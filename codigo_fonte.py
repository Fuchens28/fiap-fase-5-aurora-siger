"""Arquivo principal do Núcleo Cognitivo da Aurora Siger (NCAS).

Este e o ponto de entrada do sistema. A logica esta organizada no pacote
`ncas_core/`, cujos modulos sao descritos no README.md.

Execucao:
    python codigo_fonte.py
"""

from ncas_core.aplicacao import AplicacaoNCAS


def main() -> None:
    """Inicia o menu interativo do NCAS."""
    AplicacaoNCAS().executar()


if __name__ == "__main__":
    main()
