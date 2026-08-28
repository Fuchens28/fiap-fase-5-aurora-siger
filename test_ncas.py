"""Testes automatizados do NCAS."""

import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
from ncas_core.prompts import SimuladorIA
from ncas_core.repositorio import RepositorioColonia
from ncas_core.resiliencia import avaliar_resiliencia


class NCASTests(unittest.TestCase):
    def criar_repositorio_temporario(self, pasta: str) -> RepositorioColonia:
        """Cria um repositório isolado para cada cenário de persistência."""
        return RepositorioColonia(
            Path(pasta) / "registros.txt", Path(pasta) / "dados.json"
        )

    def test_regra_booleana(self) -> None:
        resultados = [
            MotorLogico.calcular_alerta(falha, critico)
            for falha in (False, True)
            for critico in (False, True)
        ]
        self.assertEqual(resultados, [False, False, True, True])

    def test_alerta_depende_da_falha(self) -> None:
        self.assertFalse(MotorLogico.calcular_alerta(False, False))
        self.assertFalse(MotorLogico.calcular_alerta(False, True))
        self.assertTrue(MotorLogico.calcular_alerta(True, False))
        self.assertTrue(MotorLogico.calcular_alerta(True, True))

    def test_emergencia_depende_de_falha_e_criticidade(self) -> None:
        self.assertFalse(MotorLogico.calcular_emergencia(False, True))
        self.assertFalse(MotorLogico.calcular_emergencia(True, False))
        self.assertTrue(MotorLogico.calcular_emergencia(True, True))

    def test_explicacao_menciona_de_morgan_e_simplificacao(self) -> None:
        explicacao = MotorLogico.explicar_regra()
        self.assertIn("De Morgan", explicacao)
        self.assertIn("ALERTA = FALHA", explicacao)

    def test_tabela_verdade(self) -> None:
        tabela = MotorLogico.tabela_verdade()
        self.assertEqual(len(tabela), 4)
        self.assertEqual(set(tabela[0]), {"FALHA", "CRITICO", "ALERTA"})
        self.assertTrue(tabela[-1]["ALERTA"])

    def test_rede_e_resumo_de_infraestrutura(self) -> None:
        rede = build_aurora_colony()
        resumo = resumo_rede(rede)
        self.assertEqual(len(rede.modules), 10)
        self.assertEqual(resumo["total_modulos"], 10)
        self.assertEqual(resumo["modulos_ativos"], 10)
        self.assertEqual(resumo["modulos_criticos"], 5)
        self.assertEqual(resumo["consumo_nominal_kw"], 1030.0)
        self.assertEqual(rede.modules["LSS"].status, ModuleStatus.OPERATIONAL)

    def test_impacto_de_falha_considera_dependencias_transitivas(self) -> None:
        impacto = impacto_falha(build_aurora_colony(), "PWR")
        self.assertIn("PWR", impacto)
        self.assertIn("LSS", impacto)
        self.assertIn("HAB", impacto)
        self.assertIn("RES", impacto)
        self.assertNotIn("CTL", impacto)

    def test_impacto_de_modulo_inexistente_e_vazio(self) -> None:
        self.assertEqual(impacto_falha(build_aurora_colony(), "XYZ"), [])

    def test_cenarios_prontos_alteram_status(self) -> None:
        rede = build_aurora_colony()
        self.assertEqual(len(listar_cenarios()), 4)
        self.assertEqual(aplicar_cenario(rede, "1"), "LSS")
        self.assertEqual(rede.modules["LSS"].status, ModuleStatus.SHUTDOWN)
        self.assertIsNone(aplicar_cenario(rede, "99"))

    def test_resiliencia_classifica_modulo_critico(self) -> None:
        resultado = avaliar_resiliencia(build_aurora_colony(), "LSS")
        self.assertEqual(resultado["nivel"], "CRITICO")
        self.assertIn("LSS", resultado["impacto"])
        self.assertGreater(resultado["consumo_comprometido_kw"], 500)

    def test_resiliencia_classifica_modulo_inexistente(self) -> None:
        resultado = avaliar_resiliencia(build_aurora_colony(), "XYZ")
        self.assertEqual(resultado["nivel"], "DESCONHECIDO")
        self.assertEqual(resultado["impacto"], [])

    def test_base_conhecimento_recupera_protocolo_por_modulo(self) -> None:
        base = BaseConhecimento()
        documentos = base.buscar("falha no suporte de vida LSS")
        self.assertTrue(documentos)
        self.assertEqual(documentos[0]["id"], "PROTOCOLO-LSS")

    def test_base_conhecimento_aceita_acentos(self) -> None:
        base = BaseConhecimento()
        documentos = base.buscar("comunicação")
        self.assertTrue(any(documento["id"] == "PROTOCOLO-COM" for documento in documentos))

    def test_base_conhecimento_retorna_lista_vazia_sem_resultado(self) -> None:
        self.assertEqual(BaseConhecimento().buscar("assunto inexistente"), [])

    def test_repositorio_inicia_vazio_e_gera_id(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio_temporario(pasta)
            self.assertEqual(repositorio.consultar(), [])
            self.assertEqual(repositorio.proximo_id(), 1)

    def test_proximo_id_considera_maior_id(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio_temporario(pasta)
            repositorio.adicionar(RegistroColonia(4, "data", "A", "um", False, False))
            repositorio.adicionar(RegistroColonia(9, "data", "B", "dois", False, False))
            self.assertEqual(repositorio.proximo_id(), 10)

    def test_persistencia_txt_e_json(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = RepositorioColonia(
                Path(pasta) / "registros.txt", Path(pasta) / "dados.json"
            )
            repositorio.adicionar(
                RegistroColonia(1, "2026-08-27T12:00:00", "Teste", "Falha | simulada", True, False)
            )
            repositorio.salvar_json(build_aurora_colony())

            carregado = RepositorioColonia(
                Path(pasta) / "registros.txt", Path(pasta) / "dados.json"
            )
            documento = carregado.carregar_json()
            self.assertIsNotNone(documento)
            self.assertEqual(carregado.consultar()[0].descricao, "Falha | simulada")
            self.assertEqual(documento["infraestrutura_ncas"]["total_modulos"], 10)

    def test_persistencia_preserva_multiplos_registros(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio_temporario(pasta)
            repositorio.adicionar(RegistroColonia(1, "data", "A", "primeiro", True, True))
            repositorio.adicionar(RegistroColonia(2, "data", "B", "segundo", False, True))
            recarregado = self.criar_repositorio_temporario(pasta)
            self.assertEqual(len(recarregado.consultar()), 2)
            self.assertTrue(recarregado.consultar()[0].critico)
            self.assertEqual(recarregado.consultar()[1].categoria, "B")

    def test_persistencia_preserva_historico_enriquecido(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio_temporario(pasta)
            registro = RegistroColonia(
                1,
                "data",
                "Diagnostico",
                "Falha em LSS",
                True,
                True,
                "LSS",
                ("LSS", "HAB"),
                "Ativar contingência",
                "PENDENTE",
            )
            repositorio.adicionar(registro)
            repositorio.salvar_json(build_aurora_colony())
            recarregado = self.criar_repositorio_temporario(pasta)
            recarregado.carregar_json()
            salvo = recarregado.consultar()[0]
            self.assertEqual(salvo.modulo_id, "LSS")
            self.assertEqual(salvo.impacto, ("LSS", "HAB"))
            self.assertEqual(salvo.revisao_humana, "PENDENTE")

    def test_atualizar_revisao_humana(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio_temporario(pasta)
            repositorio.adicionar(RegistroColonia(1, "data", "A", "decisão", True, True))
            self.assertTrue(repositorio.atualizar_revisao(1, "aprovada"))
            self.assertEqual(repositorio.consultar()[0].revisao_humana, "APROVADA")
            self.assertFalse(repositorio.atualizar_revisao(99, "APROVADA"))

    def test_atualizar_revisao_rejeita_status_invalido(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio_temporario(pasta)
            with self.assertRaises(ValueError):
                repositorio.atualizar_revisao(1, "IGNORADA")

    def test_arquivo_txt_inexistente_nao_gera_erro(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio_temporario(pasta)
            self.assertFalse(repositorio.avisos_leitura)

    def test_linha_txt_com_booleano_invalido_e_ignorada(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "registros.txt"
            arquivo.write_text("1|data|Teste|Descricao|talvez|False\n", encoding="utf-8")
            repositorio = RepositorioColonia(arquivo, Path(pasta) / "dados.json")
            self.assertEqual(repositorio.consultar(), [])
            self.assertEqual(len(repositorio.avisos_leitura), 1)

    def test_linha_invalida_nao_interrompe_leitura(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "registros.txt"
            arquivo.write_text("linha quebrada\n", encoding="utf-8")
            repositorio = RepositorioColonia(arquivo, Path(pasta) / "dados.json")
            self.assertEqual(repositorio.consultar(), [])
            self.assertEqual(len(repositorio.avisos_leitura), 1)

    def test_json_inexistente_retorna_none(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            repositorio = self.criar_repositorio_temporario(pasta)
            self.assertIsNone(repositorio.carregar_json())

    def test_json_invalido_levanta_erro_de_parse(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dados.json"
            arquivo.write_text("{ json quebrado", encoding="utf-8")
            repositorio = RepositorioColonia(Path(pasta) / "registros.txt", arquivo)
            with self.assertRaises(json.JSONDecodeError):
                repositorio.carregar_json()

    def test_json_com_raiz_invalida_levanta_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dados.json"
            arquivo.write_text("[]", encoding="utf-8")
            repositorio = RepositorioColonia(Path(pasta) / "registros.txt", arquivo)
            with self.assertRaises(ValueError):
                repositorio.carregar_json()

    def test_json_com_registros_invalido_levanta_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dados.json"
            arquivo.write_text('{"registros": {}}', encoding="utf-8")
            repositorio = RepositorioColonia(Path(pasta) / "registros.txt", arquivo)
            with self.assertRaises(ValueError):
                repositorio.carregar_json()

    def test_json_rejeita_campo_extra(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dados.json"
            registro = {
                "id_registro": 1,
                "data_hora": "data",
                "categoria": "Teste",
                "descricao": "Descrição",
                "falha": False,
                "critico": False,
                "campo_extra": True,
            }
            arquivo.write_text(json.dumps({"registros": [registro]}), encoding="utf-8")
            repositorio = RepositorioColonia(Path(pasta) / "registros.txt", arquivo)
            with self.assertRaises(ValueError):
                repositorio.carregar_json()

    def test_json_rejeita_tipo_invalido(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dados.json"
            registro = {
                "id_registro": "1",
                "data_hora": "data",
                "categoria": "Teste",
                "descricao": "Descrição",
                "falha": False,
                "critico": False,
            }
            arquivo.write_text(json.dumps({"registros": [registro]}), encoding="utf-8")
            repositorio = RepositorioColonia(Path(pasta) / "registros.txt", arquivo)
            with self.assertRaises(ValueError):
                repositorio.carregar_json()

    def test_carregar_json_nao_substitui_dados_em_erro(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            arquivo_txt = Path(pasta) / "registros.txt"
            arquivo_json = Path(pasta) / "dados.json"
            repositorio = RepositorioColonia(arquivo_txt, arquivo_json)
            repositorio.adicionar(RegistroColonia(1, "data", "A", "válido", True, False))
            arquivo_json.write_text("{ erro", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                repositorio.carregar_json()
            self.assertEqual(len(repositorio.consultar()), 1)

    def test_saida_estruturada_e_json_valido(self) -> None:
        saida = SimuladorIA.saida_json().split("\n", 1)[1]
        dados = json.loads(saida)
        self.assertEqual(dados["classificacao"], "ATENCAO")

    def test_prompt_zero_shot_usa_pergunta(self) -> None:
        saida = SimuladorIA.zero_shot("Qual o risco?")
        self.assertIn("Qual o risco?", saida)
        self.assertIn("ZERO-SHOT", saida)

    def test_prompt_few_shot_exibe_exemplos(self) -> None:
        saida = SimuladorIA.few_shot()
        self.assertIn("Exemplo 1", saida)
        self.assertIn("Exemplo 2", saida)

    def test_recomendacao_contextual_usa_impacto(self) -> None:
        saida = SimuladorIA.recomendacao_diagnostico(
            "LSS", "Suporte de Vida", 1, "OPERACIONAL", ["LSS", "HAB"]
        )
        self.assertIn("P1", saida)
        self.assertIn("LSS, HAB", saida)
        self.assertIn("contingência", saida)

    def test_recomendacao_para_modulo_nao_critico_indica_manutencao(self) -> None:
        saida = SimuladorIA.recomendacao_diagnostico(
            "LOG", "Logística", 4, "OPERACIONAL", ["LOG"]
        )
        self.assertIn("manutenção", saida)

    def test_diagnostico_registra_falha_simulada(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            app = AplicacaoNCAS()
            app.repositorio = self.criar_repositorio_temporario(pasta)
            saida = io.StringIO()
            with patch("builtins.input", side_effect=["LSS", "s"]), contextlib.redirect_stdout(saida):
                app.diagnosticar_infraestrutura()
            self.assertEqual(len(app.repositorio.consultar()), 1)
            self.assertTrue(app.repositorio.consultar()[0].falha)
            self.assertTrue(app.repositorio.consultar()[0].critico)
            self.assertIn("ALERTA=True", saida.getvalue())

    def test_painel_exibe_indicadores_da_colonia(self) -> None:
        app = AplicacaoNCAS()
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            app.exibir_painel()
        texto = saida.getvalue()
        self.assertIn("Módulos ativos: 10 / 10", texto)
        self.assertIn("Consumo nominal: 1030.0 kW", texto)
        self.assertIn("Dependências mapeadas", texto)

    def test_menu_encerra_com_eof(self) -> None:
        app = AplicacaoNCAS()
        saida = io.StringIO()
        with patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(saida):
            app.executar()
        self.assertIn("Encerrando o NCAS", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
