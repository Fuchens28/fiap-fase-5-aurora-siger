"""Interface de terminal do NCAS."""

from __future__ import annotations

import json
from datetime import datetime

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
from .prompts import SimuladorIA
from .repositorio import RepositorioColonia
from .resiliencia import avaliar_resiliencia


class AplicacaoNCAS:
    """Coordena menu, infraestrutura, regras e persistência."""

    def __init__(self) -> None:
        self.repositorio = RepositorioColonia()
        self.rede = build_aurora_colony()
        self.base_conhecimento = BaseConhecimento()
        if self.repositorio.avisos_leitura:
            print("Avisos durante a leitura do arquivo texto:")
            for aviso in self.repositorio.avisos_leitura:
                print(f"- {aviso}")

    @staticmethod
    def ler_booleano(pergunta: str) -> bool:
        """Converte respostas comuns do usuário para booleano."""
        while True:
            resposta = input(f"{pergunta} (s/n): ").strip().lower()
            if resposta in {"s", "sim"}:
                return True
            if resposta in {"n", "nao", "não"}:
                return False
            print("Resposta inválida. Digite s para sim ou n para não.")

    def cadastrar_registro(self) -> None:
        """Coleta e persiste um registro informado pelo usuário."""
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
        print(f"Registro {registro.id_registro} salvo com sucesso.")

    def consultar_registros(self) -> None:
        """Exibe registros carregados do arquivo texto."""
        print("\n--- Registros salvos ---")
        registros = self.repositorio.consultar()
        if not registros:
            print("Nenhum registro salvo.")
            return
        for registro in registros:
            print(
                f"#{registro.id_registro} | {registro.data_hora} | "
                f"{registro.categoria} | {registro.descricao} | "
                f"falha={registro.falha} | critico={registro.critico}"
            )

    def carregar_dados_json(self) -> None:
        """Carrega e exibe o documento JSON estruturado."""
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

    def aplicar_regra_logica(self) -> None:
        """Solicita valores booleanos e mostra resultado e demonstração."""
        print("\n--- Regra lógica de alerta ---")
        falha = self.ler_booleano("Existe uma falha")
        critico = self.ler_booleano("O evento é crítico")
        print(f"Resultado: ALERTA = {MotorLogico.calcular_alerta(falha, critico)}")
        print(MotorLogico.explicar_regra())
        print("\nTabela-verdade:")
        for linha in MotorLogico.tabela_verdade():
            print(
                f"FALHA={linha['FALHA']} | CRITICO={linha['CRITICO']} | "
                f"ALERTA={linha['ALERTA']}"
            )

    def diagnosticar_infraestrutura(self) -> None:
        """Analisa um módulo local e registra o diagnóstico."""
        print("\n--- Diagnóstico da infraestrutura ---")
        modulos = self.rede.modules
        ativos = sum(
            modulo.status == ModuleStatus.OPERATIONAL
            for modulo in modulos.values()
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
        consulta = f"{modulo.module_id} {modulo.name} falha P{modulo.priority}"
        documentos = self.base_conhecimento.buscar(consulta)
        contexto = self.base_conhecimento.formatar_contexto(documentos)
        resiliencia = avaliar_resiliencia(self.rede, modulo_id)
        recomendacao = SimuladorIA.recomendacao_diagnostico(
            modulo.module_id,
            modulo.name,
            modulo.priority,
            str(modulo.status),
            impacto_falha(self.rede, modulo_id),
            contexto,
            str(resiliencia["nivel"]),
        )
        print(f"Módulo: {modulo.module_id} - {modulo.name}")
        print(f"Status: {modulo.status} | Prioridade: P{modulo.priority}")
        print(f"Consumo nominal: {modulo.energy_consumption_kw:.1f} kW")
        print(f"FALHA={falha} | CRITICO={critico} | ALERTA={alerta}")
        print(f"EMERGENCIA={emergencia}")
        impacto = impacto_falha(self.rede, modulo_id)
        print(f"Impacto previsto: {', '.join(impacto)}")
        print(f"Resiliência: {resiliencia['nivel']}")
        print(f"Consumo comprometido: {resiliencia['consumo_comprometido_kw']} kW")
        print(f"Contexto recuperado: {contexto}")
        print("Revisão humana: PENDENTE")
        print(
            recomendacao
        )

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
        print(f"Diagnóstico registrado como #{registro.id_registro}.")

    @staticmethod
    def exibir_prompts() -> None:
        """Exibe as três estratégias de prompt simuladas."""
        print("\n--- Prompts simulados ---")
        pergunta = input("Pergunta zero-shot: ").strip() or "Qual o estado da colônia?"
        print(SimuladorIA.zero_shot(pergunta))
        print(f"\n{SimuladorIA.few_shot()}")
        print(f"\n{SimuladorIA.saida_json()}")

    def consultar_base_conhecimento(self) -> None:
        """Demonstra a etapa de recuperação do fluxo RAG local."""
        print("\n--- Base de conhecimento local (RAG) ---")
        consulta = input("Digite um tema ou módulo: ").strip()
        documentos = self.base_conhecimento.buscar(consulta)
        if not documentos:
            print("Nenhum protocolo relacionado encontrado.")
            return
        print(self.base_conhecimento.formatar_contexto(documentos))

    def exibir_painel(self) -> None:
        """Exibe uma visão consolidada da operação da colônia."""
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

    def alterar_status_modulo(self) -> None:
        """Altera o status operacional de um módulo para simulação."""
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
        """Aplica um cenário pronto ou restaura a rede original."""
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
        """Permite ao operador revisar uma decisão registrada."""
        pendentes = [
            registro
            for registro in self.repositorio.consultar()
            if registro.revisao_humana == "PENDENTE"
        ]
        print("\n--- Revisão humana ---")
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

    def executar(self) -> None:
        """Mantém o menu ativo até o usuário escolher sair."""
        opcoes = {
            "1": self.cadastrar_registro,
            "2": self.consultar_registros,
            "3": self.carregar_dados_json,
            "4": self.aplicar_regra_logica,
            "5": self.exibir_prompts,
            "6": self.diagnosticar_infraestrutura,
            "7": self.consultar_base_conhecimento,
            "8": self.exibir_painel,
            "9": self.alterar_status_modulo,
            "10": self.executar_cenario,
            "11": self.revisar_decisao,
        }
        while True:
            print(
                "\n=== NCAS | Núcleo Cognitivo da Aurora Siger ===\n"
                "1. Cadastrar registro\n"
                "2. Consultar registros\n"
                "3. Carregar dados JSON\n"
                "4. Aplicar regra lógica\n"
                "5. Exibir prompts simulados\n"
                "6. Diagnosticar infraestrutura\n"
                "7. Consultar base de conhecimento (RAG)\n"
                "8. Exibir painel operacional\n"
                "9. Alterar status de módulo\n"
                "10. Executar cenário de demonstração\n"
                "11. Revisar decisão humana\n"
                "0. Sair"
            )
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
            except (OSError, ValueError) as erro:
                print(f"Operação não concluída: {erro}")
