"""Interface de terminal do NCAS.

Concentra o menu de navegacao e os fluxos do operador. Cada opcao do menu
corresponde a um metodo desta classe, e os metodos apenas coordenam os
modulos especializados (persistencia, logica, prompts, otimizacao).
"""

from __future__ import annotations

import json
from datetime import datetime

from . import otimizacao
from .conhecimento import BaseConhecimento
from .infraestrutura import (
    aplicar_cenario,
    build_aurora_colony,
    impacto_falha,
    listar_cenarios,
    resumo_rede,
)
from .logica import MotorLogico
from .modelos import ModuleStatus, RegistroColonia
from .prompts import CatalogoPrompts, SimuladorIA
from .repositorio import RepositorioColonia
from .resiliencia import avaliar_resiliencia


class AplicacaoNCAS:
    """Coordena menu, infraestrutura, regras logicas e persistencia."""

    def __init__(self) -> None:
        self.repositorio = RepositorioColonia()
        self.rede = build_aurora_colony()
        self.base_conhecimento = BaseConhecimento()
        self.catalogo = CatalogoPrompts()
        self.modelo_risco = otimizacao.treinar()
        if self.repositorio.avisos_leitura:
            print("Avisos durante a leitura dos arquivos:")
            for aviso in self.repositorio.avisos_leitura:
                print(f"- {aviso}")

    @staticmethod
    def ler_booleano(pergunta: str) -> bool:
        """Converte as respostas comuns do usuario para booleano."""
        while True:
            resposta = input(f"{pergunta} (s/n): ").strip().lower()
            if resposta in {"s", "sim"}:
                return True
            if resposta in {"n", "nao", "não"}:
                return False
            print("Resposta inválida. Digite s para sim ou n para não.")

    def cadastrar_registro(self) -> None:
        """Coleta um evento informado pelo operador e o persiste."""
        print("\n--- Cadastro de registro ---")
        registro = RegistroColonia(
            id_registro=self.repositorio.proximo_id(),
            data_hora=datetime.now().astimezone().isoformat(timespec="seconds"),
            categoria=input("Categoria: ").strip() or "Geral",
            descricao=input("Descrição: ").strip() or "Sem descrição",
            falha=self.ler_booleano("Foi detectada uma falha"),
            critico=self.ler_booleano("A situação é crítica"),
        )
        self.repositorio.adicionar(registro)
        self.repositorio.salvar_json(self.rede)
        print(f"Registro {registro.id_registro} salvo em texto e em JSON.")

    def consultar_registros(self) -> None:
        """Exibe os registros carregados na memoria do sistema."""
        print("\n--- Registros salvos ---")
        registros = self.repositorio.consultar()
        if not registros:
            print("Nenhum registro salvo.")
            return
        for registro in registros:
            print(
                f"#{registro.id_registro} | {registro.data_hora} | "
                f"{registro.categoria} | {registro.descricao} | "
                f"falha={registro.falha} | critico={registro.critico} | "
                f"revisao={registro.revisao_humana}"
            )
        print(f"\nTotal: {len(registros)} registro(s).")
        print("Primeira linha do arquivo texto (readline):")
        print(f"  {self.repositorio.primeira_linha_txt() or '(arquivo vazio)'}")

    def carregar_dados_json(self) -> None:
        print("\n--- Carregamento do JSON ---")
        try:
            documento = self.repositorio.carregar_json()
        except (json.JSONDecodeError, TypeError, ValueError) as erro:
            print(f"Não foi possível interpretar o JSON: {erro}")
            return
        if documento is None:
            print("O arquivo dados_colonia.json ainda não existe.")
            return
        print(json.dumps(documento, ensure_ascii=False, indent=4))

    def aplicar_regra_alerta(self) -> None:
        """Regra 1: avalia o alerta e demonstra a simplificacao algebrica."""
        print("\n--- Regra 1: alerta operacional ---")
        falha = self.ler_booleano("Existe uma falha")
        critico = self.ler_booleano("O evento é crítico")
        print(f"\nALERTA      = {MotorLogico.calcular_alerta(falha, critico)}")
        print(f"EMERGENCIA  = {MotorLogico.calcular_emergencia(falha, critico)}")
        print(f"\n{MotorLogico.explicar_regra()}")
        print("\nTabela-verdade (original x simplificada):")
        print("FALHA | CRITICO | ORIGINAL | SIMPLIFICADA")
        for linha in MotorLogico.tabela_verdade():
            print(
                f"{str(linha['FALHA']):<5} | {str(linha['CRITICO']):<7} | "
                f"{str(linha['ALERTA_ORIGINAL']):<8} | "
                f"{linha['ALERTA_SIMPLIFICADO']}"
            )
        print("\nAs duas colunas são idênticas: a simplificação preserva o resultado.")

    def aplicar_regra_acesso(self) -> None:
        """Regra 2: avalia o bloqueio e demonstra o teorema de De Morgan."""
        print("\n--- Regra 2: acesso à consulta ---")
        autorizado = self.ler_booleano("O operador está autorizado")
        ativo = self.ler_booleano("O módulo está ativo")
        print(f"\nACESSO   = {MotorLogico.calcular_acesso(autorizado, ativo)}")
        print(f"BLOQUEIO = {MotorLogico.calcular_bloqueio(autorizado, ativo)}")
        print(f"\n{MotorLogico.motivo_bloqueio(autorizado, ativo)}")
        print(f"\n{MotorLogico.explicar_bloqueio()}")
        print("\nTabela-verdade (original x De Morgan):")
        print("AUTORIZADO | ATIVO | (A.B)' | A' + B'")
        for linha in MotorLogico.tabela_verdade_bloqueio():
            print(
                f"{str(linha['AUTORIZADO']):<10} | {str(linha['ATIVO']):<5} | "
                f"{str(linha['BLOQUEIO_ORIGINAL']):<6} | "
                f"{linha['BLOQUEIO_SIMPLIFICADO']}"
            )
        print("\nAs duas colunas são idênticas: De Morgan preserva o resultado.")

    def exibir_prompts(self) -> None:
        """Exibe o catalogo de prompts estruturados e a resposta simulada."""
        print("\n--- Prompts estruturados (prompts.json) ---")
        catalogo = self.catalogo.listar()
        for numero, (_, titulo, tecnica) in enumerate(catalogo, start=1):
            print(f"{numero}. [{tecnica}] {titulo}")
        print("0. Exibir todos")
        escolha = input("Escolha um prompt: ").strip()

        if escolha == "0":
            selecionados = [id_prompt for id_prompt, _, _ in catalogo]
        else:
            try:
                indice = int(escolha) - 1
                if not 0 <= indice < len(catalogo):
                    raise ValueError
            except ValueError:
                print("Opção inválida.")
                return
            selecionados = [catalogo[indice][0]]

        exemplo_alerta = (
            "LSS (Sistema de Suporte de Vida, P1) em estado DESLIGADO. "
            "Impacto em AGR, HAB e MED. 759 kW comprometidos."
        )
        variaveis = {
            "alerta": exemplo_alerta,
            "ocorrencia": exemplo_alerta,
            "registro": "LSS SHUTDOWN, 759 kW comprometidos.",
            "solicitacao": "A luminaria da bancada 3 do laboratorio queimou.",
            "ocorrencias": "A: falha no LSS (P1). B: falha no LOG (P4).",
        }
        for id_prompt in selecionados:
            print()
            print(self.catalogo.descrever(id_prompt, **variaveis))
            print("-" * 60)

    def diagnosticar_infraestrutura(self) -> None:
        """Analisa um modulo, aplica as regras e registra o diagnostico."""
        print("\n--- Diagnóstico da infraestrutura ---")
        modulos = self.rede.modules
        ativos = sum(
            modulo.status == ModuleStatus.OPERATIONAL for modulo in modulos.values()
        )
        print(f"Rede carregada: {len(modulos)} módulos | {ativos} ativos")
        modulo_id = input("ID do módulo (ex.: LSS, MED, PWR): ").strip().upper()
        modulo = modulos.get(modulo_id)
        if modulo is None:
            print("Módulo não encontrado.")
            return

        falha = modulo.status != ModuleStatus.OPERATIONAL
        falha = falha or self.ler_booleano("Simular uma falha neste módulo")
        critico = modulo.priority <= 2
        alerta = MotorLogico.calcular_alerta(falha, critico)
        emergencia = MotorLogico.calcular_emergencia(falha, critico)

        impacto = impacto_falha(self.rede, modulo_id)
        consulta = f"{modulo.module_id} {modulo.name} falha P{modulo.priority}"
        documentos = self.base_conhecimento.buscar(consulta)
        contexto = self.base_conhecimento.formatar_contexto(documentos)
        resiliencia = avaliar_resiliencia(self.rede, modulo_id)

        risco = otimizacao.prever_risco(
            self.modelo_risco,
            modulo.priority,
            len(impacto),
            float(resiliencia["consumo_comprometido_kw"]),
        )
        faixa_risco = otimizacao.classificar_risco(risco)
        texto_risco = f"{risco:.2f} ({faixa_risco})"

        recomendacao = SimuladorIA.recomendacao_diagnostico(
            modulo.module_id,
            modulo.name,
            modulo.priority,
            str(modulo.status),
            impacto,
            contexto,
            str(resiliencia["nivel"]),
            texto_risco,
        )

        print(f"\nMódulo: {modulo.module_id} - {modulo.name}")
        print(f"Status: {modulo.status} | Prioridade: P{modulo.priority}")
        print(f"Consumo nominal: {modulo.energy_consumption_kw:.1f} kW")
        print(f"FALHA={falha} | CRITICO={critico} | ALERTA={alerta}")
        print(f"EMERGENCIA={emergencia}")
        print(f"Impacto previsto: {', '.join(impacto)}")
        print(f"Resiliência: {resiliencia['nivel']}")
        print(f"Consumo comprometido: {resiliencia['consumo_comprometido_kw']} kW")
        print(f"Índice de risco (modelo otimizado): {texto_risco}")
        print(f"Contexto recuperado: {contexto}")
        print("Revisão humana: PENDENTE")
        print(recomendacao)

        registro = RegistroColonia(
            id_registro=self.repositorio.proximo_id(),
            data_hora=datetime.now().astimezone().isoformat(timespec="seconds"),
            categoria="Diagnostico de infraestrutura",
            descricao=f"{modulo.module_id}: {modulo.status}",
            falha=falha,
            critico=critico,
            modulo_id=modulo.module_id,
            impacto=tuple(impacto),
            recomendacao=recomendacao,
        )
        self.repositorio.adicionar(registro)
        self.repositorio.salvar_json(self.rede)
        print(f"\nDiagnóstico registrado como #{registro.id_registro}.")

    def consultar_base_conhecimento(self) -> None:
        """Demonstra a etapa de recuperacao de contexto do fluxo RAG local."""
        print("\n--- Base de conhecimento local (RAG) ---")
        consulta = input("Digite um tema ou módulo: ").strip()
        documentos = self.base_conhecimento.buscar(consulta)
        if not documentos:
            print("Nenhum protocolo relacionado encontrado.")
            return
        print(self.base_conhecimento.formatar_contexto(documentos))

    def otimizar_indice_risco(self) -> None:
        """Exibe o ajuste do modelo de risco por gradiente descendente."""
        print("\n--- Otimização do índice de risco ---")
        print(otimizacao.relatorio(self.modelo_risco))
        print("\nPrevisão para os módulos da colônia:")
        for modulo in self.rede.modules.values():
            impacto = impacto_falha(self.rede, modulo.module_id)
            consumo = sum(
                self.rede.modules[item].energy_consumption_kw for item in impacto
            )
            risco = otimizacao.prever_risco(
                self.modelo_risco, modulo.priority, len(impacto), consumo
            )
            print(
                f"  {modulo.module_id:<4} P{modulo.priority} | "
                f"{len(impacto)} módulo(s) | {consumo:7.1f} kW | "
                f"risco={risco:.2f} ({otimizacao.classificar_risco(risco)})"
            )

    def exibir_painel(self) -> None:
        """Exibe uma visao consolidada da operacao da colonia."""
        resumo = resumo_rede(self.rede)
        registros = self.repositorio.consultar()
        print("\n--- Painel operacional da colônia ---")
        print(f"Módulos ativos: {resumo['modulos_ativos']} / {resumo['total_modulos']}")
        print(f"Módulos críticos: {resumo['modulos_criticos']}")
        print(f"Consumo nominal: {resumo['consumo_nominal_kw']} kW")
        print(f"Dependências mapeadas: {resumo['total_dependencias']}")
        print(f"Registros realizados: {len(registros)}")
        print(f"Alertas registrados: {sum(registro.falha for registro in registros)}")
        print(
            "Emergências registradas: "
            f"{sum(registro.falha and registro.critico for registro in registros)}"
        )
        print(
            "Revisões pendentes: "
            f"{sum(registro.revisao_humana == 'PENDENTE' for registro in registros)}"
        )

    def alterar_status_modulo(self) -> None:
        """Altera o status operacional de um modulo, para simulacao."""
        print("\n--- Alteração de status ---")
        modulo_id = input("ID do módulo: ").strip().upper()
        modulo = self.rede.modules.get(modulo_id)
        if modulo is None:
            print("Módulo não encontrado.")
            return
        print("1. OPERACIONAL\n2. DEGRADADO\n3. SOBREVIVENCIA\n4. DESLIGADO")
        escolha = input("Novo status: ").strip()
        status = {
            "1": ModuleStatus.OPERATIONAL,
            "2": ModuleStatus.DEGRADED,
            "3": ModuleStatus.SURVIVAL,
            "4": ModuleStatus.SHUTDOWN,
        }.get(escolha)
        if status is None:
            print("Status inválido.")
            return
        modulo.status = status
        print(f"Status de {modulo_id} alterado para {status}.")

    def executar_cenario(self) -> None:
        """Aplica um cenario pronto ou restaura a rede original."""
        print("\n--- Cenários de demonstração ---")
        for codigo, descricao in listar_cenarios():
            print(f"{codigo}. {descricao}")
        print("0. Restaurar infraestrutura")
        escolha = input("Cenário: ").strip()
        if escolha == "0":
            self.rede = build_aurora_colony()
            print("Infraestrutura restaurada.")
            return
        modulo_id = aplicar_cenario(self.rede, escolha)
        if modulo_id is None:
            print("Cenário inválido.")
            return
        print(f"Cenário aplicado ao módulo {modulo_id}.")

    def revisar_decisao(self) -> None:
        """Permite ao operador aprovar ou rejeitar uma decisao registrada."""
        print("\n--- Revisão humana ---")
        pendentes = [
            registro
            for registro in self.repositorio.consultar()
            if registro.revisao_humana == "PENDENTE"
        ]
        if not pendentes:
            print("Nenhuma decisão pendente.")
            return
        for registro in pendentes:
            print(f"#{registro.id_registro} | {registro.descricao}")
        try:
            id_registro = int(input("ID do registro: ").strip())
        except ValueError:
            print("ID inválido.")
            return
        print("1. Aprovar\n2. Rejeitar\n3. Manter pendente")
        escolha = input("Decisão: ").strip()
        status = {"1": "APROVADA", "2": "REJEITADA", "3": "PENDENTE"}.get(escolha)
        if status is None:
            print("Decisão inválida.")
            return
        if not self.repositorio.atualizar_revisao(id_registro, status):
            print("Registro não encontrado.")
            return
        self.repositorio.salvar_json(self.rede)
        print(f"Registro #{id_registro} atualizado para {status}.")

    MENU = (
        "\n=== NCAS | Núcleo Cognitivo da Aurora Siger ===\n"
        "-- Registros e arquivos --\n"
        " 1. Cadastrar registro (texto + JSON)\n"
        " 2. Consultar registros salvos\n"
        " 3. Carregar dados do arquivo JSON\n"
        "-- Regras lógicas --\n"
        " 4. Regra de alerta (teoremas de simplificação)\n"
        " 5. Regra de acesso (teorema de De Morgan)\n"
        "-- Inteligência simulada --\n"
        " 6. Exibir prompts estruturados\n"
        " 7. Diagnosticar infraestrutura\n"
        " 8. Consultar base de conhecimento (RAG)\n"
        " 9. Otimizar índice de risco (MSE)\n"
        "-- Operação --\n"
        "10. Exibir painel operacional\n"
        "11. Alterar status de módulo\n"
        "12. Executar cenário de demonstração\n"
        "13. Revisar decisão humana\n"
        " 0. Sair"
    )

    def executar(self) -> None:
        """Mantem o menu ativo ate o operador escolher sair."""
        opcoes = {
            "1": self.cadastrar_registro,
            "2": self.consultar_registros,
            "3": self.carregar_dados_json,
            "4": self.aplicar_regra_alerta,
            "5": self.aplicar_regra_acesso,
            "6": self.exibir_prompts,
            "7": self.diagnosticar_infraestrutura,
            "8": self.consultar_base_conhecimento,
            "9": self.otimizar_indice_risco,
            "10": self.exibir_painel,
            "11": self.alterar_status_modulo,
            "12": self.executar_cenario,
            "13": self.revisar_decisao,
        }
        while True:
            print(self.MENU)
            try:
                escolha = input("Escolha uma opção: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nEncerrando o NCAS.")
                return
            if escolha == "0":
                print("Encerrando o NCAS.")
                return
            acao = opcoes.get(escolha)
            if acao is None:
                print("Opção inválida.")
                continue
            try:
                acao()
            except (EOFError, KeyboardInterrupt):
                print("\nEncerrando o NCAS.")
                return
            except (OSError, ValueError) as erro:
                print(f"Operação não concluída: {erro}")
