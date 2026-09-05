"""Testes automatizados do NCAS.

Executar com:
    python -m unittest discover -v
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ncas_core import otimizacao
from ncas_core.aplicacao import AplicacaoNCAS
from ncas_core.conhecimento import BaseConhecimento
from ncas_core.infraestrutura import (
    aplicar_cenario,
    build_aurora_colony,
    impacto_falha,
    listar_cenarios,
    resumo_rede,
)
from ncas_core.logica import MotorLogico
from ncas_core.modelos import ModuleStatus, RegistroColonia
from ncas_core.prompts import CatalogoPrompts, SimuladorIA
from ncas_core.repositorio import RepositorioColonia
from ncas_core.resiliencia import avaliar_resiliencia


def registro_exemplo(id_registro: int = 1, **campos) -> RegistroColonia:
    """Cria um registro com valores padrao, sobrescritos por ``campos``."""
    dados = {
        "id_registro": id_registro,
        "data_hora": "2026-09-04T10:00:00-03:00",
        "categoria": "Diagnostico de infraestrutura",
        "descricao": "LSS: DESLIGADO",
        "falha": True,
        "critico": True,
    }
    dados.update(campos)
    return RegistroColonia(**dados)


class RegraAlertaTests(unittest.TestCase):
    """Regra 1: simplificacao por teoremas de simplificacao."""

    def test_regra_original_cobre_as_quatro_combinacoes(self) -> None:
        resultados = [
            MotorLogico.calcular_alerta(falha, critico)
            for falha in (False, True)
            for critico in (False, True)
        ]
        self.assertEqual(resultados, [False, False, True, True])

    def test_forma_simplificada_equivale_a_original(self) -> None:
        for falha in (False, True):
            for critico in (False, True):
                with self.subTest(falha=falha, critico=critico):
                    self.assertEqual(
                        MotorLogico.calcular_alerta(falha, critico),
                        MotorLogico.calcular_alerta_simplificado(falha, critico),
                    )

    def test_emergencia_exige_falha_e_criticidade(self) -> None:
        self.assertTrue(MotorLogico.calcular_emergencia(True, True))
        self.assertFalse(MotorLogico.calcular_emergencia(True, False))
        self.assertFalse(MotorLogico.calcular_emergencia(False, True))

    def test_tabela_verdade_compara_as_duas_formas(self) -> None:
        tabela = MotorLogico.tabela_verdade()
        self.assertEqual(len(tabela), 4)
        self.assertEqual(
            set(tabela[0]),
            {"FALHA", "CRITICO", "ALERTA_ORIGINAL", "ALERTA_SIMPLIFICADO"},
        )
        for linha in tabela:
            self.assertEqual(linha["ALERTA_ORIGINAL"], linha["ALERTA_SIMPLIFICADO"])

    def test_explicacao_cita_os_teoremas_aplicados(self) -> None:
        texto = MotorLogico.explicar_regra()
        self.assertIn("Distributividade", texto)
        self.assertIn("Complementaridade", texto)
        self.assertIn("Identidade do produto", texto)
        self.assertIn("ALERTA = FALHA", texto)


class RegraBloqueioTests(unittest.TestCase):
    """Regra 2: simplificacao pelo primeiro teorema de De Morgan."""

    def test_acesso_exige_autorizacao_e_modulo_ativo(self) -> None:
        self.assertTrue(MotorLogico.calcular_acesso(True, True))
        self.assertFalse(MotorLogico.calcular_acesso(True, False))
        self.assertFalse(MotorLogico.calcular_acesso(False, True))
        self.assertFalse(MotorLogico.calcular_acesso(False, False))

    def test_de_morgan_preserva_o_resultado(self) -> None:
        for autorizado in (False, True):
            for ativo in (False, True):
                with self.subTest(autorizado=autorizado, ativo=ativo):
                    self.assertEqual(
                        MotorLogico.calcular_bloqueio(autorizado, ativo),
                        MotorLogico.calcular_bloqueio_simplificado(autorizado, ativo),
                    )

    def test_tabela_verdade_do_bloqueio(self) -> None:
        tabela = MotorLogico.tabela_verdade_bloqueio()
        self.assertEqual(len(tabela), 4)
        for linha in tabela:
            self.assertEqual(
                linha["BLOQUEIO_ORIGINAL"], linha["BLOQUEIO_SIMPLIFICADO"]
            )

    def test_motivo_isola_a_causa_do_bloqueio(self) -> None:
        self.assertIn("não autorizado", MotorLogico.motivo_bloqueio(False, True))
        self.assertIn("inativo", MotorLogico.motivo_bloqueio(True, False))
        motivo_duplo = MotorLogico.motivo_bloqueio(False, False)
        self.assertIn("não autorizado", motivo_duplo)
        self.assertIn("inativo", motivo_duplo)
        self.assertIn("liberado", MotorLogico.motivo_bloqueio(True, True))

    def test_explicacao_cita_o_teorema(self) -> None:
        texto = MotorLogico.explicar_bloqueio()
        self.assertIn("De Morgan", texto)
        self.assertIn("(A . B)' = A' + B'", texto)


class InfraestruturaTests(unittest.TestCase):
    def test_rede_possui_dez_modulos_operacionais(self) -> None:
        rede = build_aurora_colony()
        self.assertEqual(len(rede.modules), 10)
        self.assertTrue(
            all(
                modulo.status == ModuleStatus.OPERATIONAL
                for modulo in rede.modules.values()
            )
        )

    def test_resumo_calcula_indicadores(self) -> None:
        resumo = resumo_rede(build_aurora_colony())
        self.assertEqual(resumo["total_modulos"], 10)
        self.assertEqual(resumo["modulos_criticos"], 5)
        self.assertEqual(resumo["consumo_nominal_kw"], 1030.0)
        self.assertEqual(resumo["total_dependencias"], 14)

    def test_impacto_e_transitivo(self) -> None:
        rede = build_aurora_colony()
        # PWR alimenta 8 modulos dependentes; o CTL opera com fonte propria.
        self.assertEqual(len(impacto_falha(rede, "PWR")), 9)
        self.assertNotIn("CTL", impacto_falha(rede, "PWR"))
        self.assertEqual(impacto_falha(rede, "LSS"), ["AGR", "HAB", "LSS", "MED"])
        self.assertEqual(impacto_falha(rede, "RES"), ["RES"])

    def test_impacto_de_modulo_inexistente_e_vazio(self) -> None:
        self.assertEqual(impacto_falha(build_aurora_colony(), "XXX"), [])

    def test_cenarios_prontos_alteram_status(self) -> None:
        rede = build_aurora_colony()
        self.assertEqual(aplicar_cenario(rede, "1"), "LSS")
        self.assertEqual(rede.modules["LSS"].status, ModuleStatus.SHUTDOWN)
        self.assertIsNone(aplicar_cenario(rede, "99"))
        self.assertEqual(len(listar_cenarios()), 4)


class ResilienciaTests(unittest.TestCase):
    def test_modulo_p1_e_classificado_como_critico(self) -> None:
        resultado = avaliar_resiliencia(build_aurora_colony(), "LSS")
        self.assertEqual(resultado["nivel"], "CRITICO")
        self.assertEqual(resultado["consumo_comprometido_kw"], 759.0)

    def test_modulo_isolado_tem_nivel_moderado(self) -> None:
        resultado = avaliar_resiliencia(build_aurora_colony(), "RES")
        self.assertEqual(resultado["nivel"], "MODERADO")

    def test_modulo_inexistente_retorna_desconhecido(self) -> None:
        resultado = avaliar_resiliencia(build_aurora_colony(), "XXX")
        self.assertEqual(resultado["nivel"], "DESCONHECIDO")


class PersistenciaTests(unittest.TestCase):
    """Manipulacao de arquivos texto e JSON."""

    def criar_repositorio(self, pasta: str) -> RepositorioColonia:
        return RepositorioColonia(
            Path(pasta) / "registros.txt", Path(pasta) / "dados.json"
        )

    def test_grava_e_recupera_registro_no_texto(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            repositorio.adicionar(registro_exemplo(1))
            recarregado = self.criar_repositorio(pasta)
            self.assertEqual(len(recarregado.consultar()), 1)
            self.assertEqual(recarregado.consultar()[0].descricao, "LSS: DESLIGADO")

    def test_proximo_id_incrementa(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            self.assertEqual(repositorio.proximo_id(), 1)
            repositorio.adicionar(registro_exemplo(1))
            self.assertEqual(repositorio.proximo_id(), 2)

    def test_json_preserva_campos_ausentes_no_texto(self) -> None:
        """Regressao: os campos ricos nao podem sumir ao reiniciar o sistema."""
        with tempfile.TemporaryDirectory() as pasta:
            rede = build_aurora_colony()
            repositorio = self.criar_repositorio(pasta)
            repositorio.adicionar(
                registro_exemplo(
                    1,
                    modulo_id="LSS",
                    impacto=("AGR", "HAB", "LSS", "MED"),
                    recomendacao="Ativar contingência",
                )
            )
            repositorio.atualizar_revisao(1, "APROVADA")
            repositorio.salvar_json(rede)

            reiniciado = self.criar_repositorio(pasta)
            reiniciado.salvar_json(rede)
            registro = reiniciado.consultar()[0]
            self.assertEqual(registro.modulo_id, "LSS")
            self.assertEqual(registro.impacto, ("AGR", "HAB", "LSS", "MED"))
            self.assertEqual(registro.recomendacao, "Ativar contingência")
            self.assertEqual(registro.revisao_humana, "APROVADA")

    def test_separador_no_texto_nao_quebra_o_formato(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            repositorio.adicionar(
                registro_exemplo(1, descricao="falha em A | B | C")
            )
            recarregado = RepositorioColonia(
                Path(pasta) / "registros.txt", Path(pasta) / "inexistente.json"
            )
            self.assertEqual(len(recarregado.consultar()), 1)
            self.assertEqual(recarregado.avisos_leitura, [])

    def test_descricao_com_acentos_sobrevive_ao_ciclo(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            repositorio.adicionar(
                registro_exemplo(1, descricao="Pressão da atmosfera não estável")
            )
            recarregado = RepositorioColonia(
                Path(pasta) / "registros.txt", Path(pasta) / "inexistente.json"
            )
            self.assertEqual(
                recarregado.consultar()[0].descricao,
                "Pressão da atmosfera não estável",
            )

    def test_linha_invalida_e_ignorada_com_aviso(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "registros.txt"
            caminho.write_text(
                "1|2026-09-04T10:00:00|Teste|Ok|True|False\n"
                "linha quebrada\n"
                "3|2026-09-04T10:00:00|Teste|Ok|talvez|False\n",
                encoding="utf-8",
            )
            repositorio = RepositorioColonia(caminho, Path(pasta) / "inexistente.json")
            self.assertEqual(len(repositorio.consultar()), 1)
            self.assertEqual(len(repositorio.avisos_leitura), 2)

    def test_texto_inexistente_nao_gera_erro(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            self.assertEqual(repositorio.consultar(), [])
            self.assertEqual(repositorio.ler_txt_bruto(), "")
            self.assertEqual(repositorio.primeira_linha_txt(), "")

    def test_metodos_de_leitura_do_capitulo_3(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            repositorio.adicionar(registro_exemplo(1))
            repositorio.adicionar(registro_exemplo(2, descricao="COM: DEGRADADO"))
            bruto = repositorio.ler_txt_bruto()
            self.assertEqual(len(bruto.strip().splitlines()), 2)
            self.assertTrue(repositorio.primeira_linha_txt().startswith("1|"))

    def test_reescrever_txt_sincroniza_com_a_memoria(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            repositorio.adicionar(registro_exemplo(1))
            repositorio.adicionar(registro_exemplo(2))
            repositorio.registros.pop()
            repositorio.reescrever_txt()
            self.assertEqual(
                len(repositorio.ler_txt_bruto().strip().splitlines()), 1
            )

    def test_json_salvo_contem_resumo_da_rede(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            repositorio.adicionar(registro_exemplo(1))
            repositorio.salvar_json(build_aurora_colony())
            documento = json.loads(
                (Path(pasta) / "dados.json").read_text(encoding="utf-8")
            )
            self.assertEqual(documento["total_registros"], 1)
            self.assertEqual(documento["infraestrutura_ncas"]["total_modulos"], 10)

    def test_json_inexistente_retorna_none(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            self.assertIsNone(self.criar_repositorio(pasta).carregar_json())

    def test_json_malformado_gera_erro(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "dados.json"
            caminho.write_text("{isso nao e json", encoding="utf-8")
            repositorio = RepositorioColonia(Path(pasta) / "registros.txt", caminho)
            self.assertTrue(repositorio.avisos_leitura)
            with self.assertRaises(json.JSONDecodeError):
                repositorio.carregar_json()

    def test_json_com_tipos_invalidos_e_recusado(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "dados.json"
            caminho.write_text(
                json.dumps(
                    {
                        "registros": [
                            {
                                "id_registro": "um",
                                "data_hora": "x",
                                "categoria": "y",
                                "descricao": "z",
                                "falha": True,
                                "critico": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            repositorio = RepositorioColonia(Path(pasta) / "registros.txt", caminho)
            with self.assertRaises(ValueError):
                repositorio.carregar_json()
            # O estado anterior nao foi corrompido pela leitura invalida.
            self.assertEqual(repositorio.consultar(), [])

    def test_json_com_campo_desconhecido_e_recusado(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "dados.json"
            caminho.write_text(
                json.dumps(
                    {
                        "registros": [
                            {
                                "id_registro": 1,
                                "data_hora": "x",
                                "categoria": "y",
                                "descricao": "z",
                                "falha": True,
                                "critico": False,
                                "campo_extra": 1,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            repositorio = RepositorioColonia(Path(pasta) / "registros.txt", caminho)
            with self.assertRaises(ValueError):
                repositorio.carregar_json()

    def test_revisao_humana_valida_o_status(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio(pasta)
            repositorio.adicionar(registro_exemplo(1))
            self.assertTrue(repositorio.atualizar_revisao(1, "aprovada"))
            self.assertEqual(repositorio.consultar()[0].revisao_humana, "APROVADA")
            self.assertFalse(repositorio.atualizar_revisao(99, "APROVADA"))
            with self.assertRaises(ValueError):
                repositorio.atualizar_revisao(1, "TALVEZ")


class ConhecimentoTests(unittest.TestCase):
    def test_busca_encontra_protocolo_por_palavra_chave(self) -> None:
        documentos = BaseConhecimento().buscar("falha no lss")
        self.assertTrue(documentos)
        self.assertEqual(documentos[0]["id"], "PROTOCOLO-LSS")

    def test_busca_tolera_acentos(self) -> None:
        base = BaseConhecimento()
        self.assertEqual(
            [d["id"] for d in base.buscar("comunicação")],
            [d["id"] for d in base.buscar("comunicacao")],
        )

    def test_busca_sem_resultado_gera_contexto_padrao(self) -> None:
        base = BaseConhecimento()
        self.assertIn("Nenhum protocolo", base.formatar_contexto(base.buscar("xyz")))


class PromptsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalogo = CatalogoPrompts()

    def test_catalogo_cobre_as_tecnicas_exigidas(self) -> None:
        tecnicas = {tecnica for _, _, tecnica in self.catalogo.listar()}
        self.assertIn("zero-shot", tecnicas)
        self.assertIn("few-shot", tecnicas)
        self.assertIn("structured output", tecnicas)
        self.assertIn("chain-of-thought", tecnicas)

    def test_prompt_renderizado_contem_os_quatro_elementos(self) -> None:
        texto = self.catalogo.renderizar("resumir_alerta", alerta="LSS desligado")
        prompt = self.catalogo.obter("resumir_alerta")
        self.assertIn(prompt["tarefa"], texto)
        self.assertIn(prompt["contexto"], texto)
        self.assertIn(prompt["formato_saida"], texto)
        self.assertIn("LSS desligado", texto)

    def test_few_shot_inclui_os_exemplos(self) -> None:
        texto = self.catalogo.renderizar(
            "classificar_solicitacao", solicitacao="A bomba parou."
        )
        self.assertIn("EMERGENCIA", texto)
        self.assertIn("A bomba parou.", texto)

    def test_variavel_ausente_vira_marcador_explicito(self) -> None:
        texto = self.catalogo.renderizar("resumir_alerta")
        self.assertIn("<alerta não informado>", texto)

    def test_saida_estruturada_declara_contrato_json(self) -> None:
        prompt = self.catalogo.obter("diagnostico_estruturado")
        self.assertIn("JSON", prompt["formato_saida"])
        self.assertEqual(json.loads(prompt["resposta_simulada"])["confianca"], 0.92)

    def test_prompt_inexistente_gera_erro(self) -> None:
        with self.assertRaises(ValueError):
            self.catalogo.renderizar("nao_existe")

    def test_descrever_mostra_prompt_e_resposta(self) -> None:
        texto = self.catalogo.descrever("resumir_alerta", alerta="LSS desligado")
        self.assertIn("PROMPT ENVIADO", texto)
        self.assertIn("RESPOSTA SIMULADA", texto)

    def test_simulador_zero_shot_e_few_shot(self) -> None:
        self.assertIn("[ZERO-SHOT]", SimuladorIA.zero_shot("Qual o risco?"))
        self.assertIn("[FEW-SHOT]", SimuladorIA.few_shot())

    def test_simulador_produz_json_valido(self) -> None:
        saida = SimuladorIA.saida_json()
        corpo = saida.split("\n", 1)[1]
        self.assertEqual(json.loads(corpo)["origem"], "simulacao_NCAS")

    def test_recomendacao_para_modulo_critico(self) -> None:
        saida = SimuladorIA.recomendacao_diagnostico(
            "LSS", "Suporte de Vida", 1, "DESLIGADO", ["LSS", "HAB"]
        )
        self.assertIn("contingência", saida)
        self.assertIn("LSS, HAB", saida)

    def test_recomendacao_para_modulo_nao_critico(self) -> None:
        saida = SimuladorIA.recomendacao_diagnostico(
            "LOG", "Logística", 4, "OPERACIONAL", ["LOG"]
        )
        self.assertIn("manutenção", saida)


class OtimizacaoTests(unittest.TestCase):
    def test_mse_de_previsao_perfeita_e_zero(self) -> None:
        amostras = [([1.0, 1.0], 2.0), ([1.0, 0.0], 1.0)]
        self.assertEqual(otimizacao.erro_quadratico_medio([1.0, 1.0], amostras), 0.0)

    def test_mse_penaliza_desvios_maiores(self) -> None:
        amostras = [([1.0], 1.0)]
        erro_pequeno = otimizacao.erro_quadratico_medio([0.9], amostras)
        erro_grande = otimizacao.erro_quadratico_medio([0.5], amostras)
        self.assertLess(erro_pequeno, erro_grande)

    def test_gradiente_descendente_reduz_o_erro(self) -> None:
        resultado = otimizacao.treinar()
        self.assertLess(resultado.mse_final, resultado.mse_inicial)
        self.assertGreater(resultado.reducao_percentual, 90.0)

    def test_pesos_ficam_finitos_em_toda_a_faixa_de_lambda(self) -> None:
        for lambda_l2 in (0.0, 0.01, 0.1, 0.5, 1.0):
            with self.subTest(lambda_l2=lambda_l2):
                resultado = otimizacao.treinar(regularizacao=lambda_l2)
                self.assertTrue(all(abs(peso) < 100 for peso in resultado.pesos))

    def test_regularizacao_maior_reduz_a_magnitude_dos_pesos(self) -> None:
        comparacao = otimizacao.comparar_regularizacao((0.0, 0.1, 1.0))
        magnitudes = [magnitude for _, _, magnitude in comparacao]
        self.assertEqual(magnitudes, sorted(magnitudes, reverse=True))

    def test_regularizacao_maior_aumenta_o_erro_no_historico(self) -> None:
        comparacao = otimizacao.comparar_regularizacao((0.0, 0.1, 1.0))
        erros = [mse for _, mse, _ in comparacao]
        self.assertEqual(erros, sorted(erros))

    def test_risco_cresce_com_a_gravidade(self) -> None:
        modelo = otimizacao.treinar()
        risco_critico = otimizacao.prever_risco(modelo, 1, 9, 1030.0)
        risco_baixo = otimizacao.prever_risco(modelo, 5, 1, 41.0)
        self.assertGreater(risco_critico, risco_baixo)

    def test_risco_permanece_no_intervalo_valido(self) -> None:
        modelo = otimizacao.treinar()
        for prioridade in range(1, 6):
            risco = otimizacao.prever_risco(modelo, prioridade, 10, 5000.0)
            self.assertGreaterEqual(risco, 0.0)
            self.assertLessEqual(risco, 1.0)

    def test_classificacao_por_faixa(self) -> None:
        self.assertEqual(otimizacao.classificar_risco(0.95), "CRITICO")
        self.assertEqual(otimizacao.classificar_risco(0.70), "ALTO")
        self.assertEqual(otimizacao.classificar_risco(0.40), "MODERADO")
        self.assertEqual(otimizacao.classificar_risco(0.10), "BAIXO")

    def test_historico_vazio_nao_quebra_o_treino(self) -> None:
        resultado = otimizacao.treinar(historico=[])
        self.assertEqual(resultado.pesos, [])
        self.assertEqual(otimizacao.prever_risco(resultado, 1, 1, 1.0), 0.0)
        self.assertIn("Não há histórico", otimizacao.relatorio(resultado))

    def test_relatorio_cita_os_conceitos_do_capitulo(self) -> None:
        texto = otimizacao.relatorio(otimizacao.treinar())
        self.assertIn("erro quadrático médio", texto)
        self.assertIn("Regularização L2", texto)


class AplicacaoTests(unittest.TestCase):
    """Fluxos do menu, com entrada e saida simuladas."""

    def executar_menu(self, entradas: list[str]) -> str:
        buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as pasta:
            with contextlib.redirect_stdout(buffer):
                with patch("builtins.input", side_effect=entradas):
                    aplicacao = AplicacaoNCAS()
                    aplicacao.repositorio = RepositorioColonia(
                        Path(pasta) / "registros.txt", Path(pasta) / "dados.json"
                    )
                    aplicacao.executar()
        return buffer.getvalue()

    def test_menu_encerra_com_a_opcao_zero(self) -> None:
        self.assertIn("Encerrando o NCAS.", self.executar_menu(["0"]))

    def test_menu_avisa_opcao_invalida(self) -> None:
        self.assertIn("Opção inválida.", self.executar_menu(["99", "0"]))

    def test_menu_encerra_com_seguranca_no_fim_da_entrada(self) -> None:
        # StopIteration do mock simula EOF: o menu nao pode estourar excecao.
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with patch("builtins.input", side_effect=EOFError):
                AplicacaoNCAS().executar()
        self.assertIn("Encerrando o NCAS.", buffer.getvalue())

    def test_regra_de_alerta_exibe_tabela_e_simplificacao(self) -> None:
        saida = self.executar_menu(["4", "s", "n", "0"])
        self.assertIn("ALERTA      = True", saida)
        self.assertIn("ALERTA = FALHA", saida)
        self.assertIn("são idênticas", saida)

    def test_regra_de_acesso_exibe_de_morgan(self) -> None:
        saida = self.executar_menu(["5", "n", "s", "0"])
        self.assertIn("BLOQUEIO = True", saida)
        self.assertIn("De Morgan", saida)
        self.assertIn("não autorizado", saida)

    def test_cadastro_persiste_registro(self) -> None:
        saida = self.executar_menu(
            ["1", "Manutencao", "Troca de filtro", "n", "n", "2", "0"]
        )
        self.assertIn("salvo em texto e em JSON", saida)
        self.assertIn("Troca de filtro", saida)

    def test_diagnostico_critico_gera_alerta_e_registro(self) -> None:
        saida = self.executar_menu(["7", "LSS", "s", "0"])
        self.assertIn("FALHA=True | CRITICO=True | ALERTA=True", saida)
        self.assertIn("EMERGENCIA=True", saida)
        self.assertIn("AGR, HAB, LSS, MED", saida)
        self.assertIn("Índice de risco", saida)
        self.assertIn("Diagnóstico registrado", saida)

    def test_diagnostico_de_modulo_inexistente(self) -> None:
        self.assertIn("Módulo não encontrado.", self.executar_menu(["7", "XXX", "0"]))

    def test_prompts_exibem_catalogo_completo(self) -> None:
        saida = self.executar_menu(["6", "0", "0"])
        self.assertIn("PROMPT ENVIADO", saida)
        self.assertIn("[ZERO-SHOT]", saida)
        self.assertIn("[FEW-SHOT]", saida)
        self.assertIn("[CHAIN-OF-THOUGHT]", saida)

    def test_otimizacao_exibe_relatorio_e_previsoes(self) -> None:
        saida = self.executar_menu(["9", "0"])
        self.assertIn("MSE inicial", saida)
        self.assertIn("MSE final", saida)
        self.assertIn("Previsão para os módulos", saida)

    def test_rag_recupera_protocolo(self) -> None:
        saida = self.executar_menu(["8", "comunicação", "0"])
        self.assertIn("canal redundante", saida)

    def test_painel_exibe_indicadores(self) -> None:
        saida = self.executar_menu(["10", "0"])
        self.assertIn("Módulos ativos: 10 / 10", saida)
        self.assertIn("Consumo nominal: 1030.0 kW", saida)

    def test_cenario_altera_a_rede(self) -> None:
        saida = self.executar_menu(["12", "1", "0"])
        self.assertIn("Cenário aplicado ao módulo LSS", saida)

    def test_revisao_humana_aprova_diagnostico(self) -> None:
        saida = self.executar_menu(["7", "LSS", "s", "13", "1", "1", "0"])
        self.assertIn("atualizado para APROVADA", saida)


if __name__ == "__main__":
    unittest.main()
