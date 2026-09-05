"""Persistencia do NCAS em arquivo texto e em arquivo JSON.

Este modulo concentra a manipulacao de arquivos estudada no Capitulo 3:

- funcao ``open()`` e o gerenciador de contexto ``with``;
- modos de abertura ``"r"`` (leitura), ``"a"`` (append) e ``"w"`` (escrita);
- metodos ``readlines()``, ``readline()``, ``read()`` e ``writelines()``;
- leitura e gravacao de dicionarios com a biblioteca ``json``.

Divisao de responsabilidades entre os dois arquivos:

- ``registros_colonia.txt`` e o log operacional. Cada linha e um evento em
  formato delimitado por ``|``, legivel por humanos e escrito em modo append.
- ``dados_colonia.json`` e a base estruturada. Guarda o registro completo
  (inclusive impacto, recomendacao e revisao humana) e o resumo da rede.

O JSON e a fonte primaria na carga: o texto so e usado quando o JSON ainda
nao existe ou esta invalido. Isso evita que campos presentes apenas no JSON
sejam perdidos ao reiniciar o sistema.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .infraestrutura import resumo_rede
from .modelos import RedeInfraestrutura, RegistroColonia

SEPARADOR = "|"

REVISOES_VALIDAS = {"PENDENTE", "APROVADA", "REJEITADA"}


class RepositorioColonia:
    """Le, valida e grava os registros da colonia em texto e em JSON."""

    def __init__(
        self,
        arquivo_txt: str | Path = "registros_colonia.txt",
        arquivo_json: str | Path = "dados_colonia.json",
    ) -> None:
        self.arquivo_txt = Path(arquivo_txt)
        self.arquivo_json = Path(arquivo_json)
        self.registros: list[RegistroColonia] = []
        self.avisos_leitura: list[str] = []
        self.carregar()

    def carregar(self) -> None:
        """Carrega o estado do sistema priorizando o JSON estruturado.

        O arquivo texto guarda apenas seis campos por linha. Se ele fosse a
        fonte primaria, o impacto, a recomendacao e a revisao humana seriam
        perdidos a cada reinicio. Por isso o JSON e lido primeiro e o texto
        funciona como plano de recuperacao.
        """
        self.registros = []
        self.avisos_leitura = []
        try:
            if self.carregar_json() is not None:
                return
        except (OSError, ValueError, json.JSONDecodeError) as erro:
            self.avisos_leitura.append(
                f"JSON ignorado na carga inicial ({erro}). Usando o arquivo texto."
            )
            self.registros = []
        self.carregar_txt()

    def proximo_id(self) -> int:
        return max((registro.id_registro for registro in self.registros), default=0) + 1

    def adicionar(self, registro: RegistroColonia) -> None:
        """Grava o registro no arquivo texto e so entao confirma em memoria.

        Usa o modo append (``"a"``) para preservar o historico ja gravado e o
        metodo ``writelines()`` para escrever a linha do evento.
        """
        self.arquivo_txt.parent.mkdir(parents=True, exist_ok=True)
        with open(self.arquivo_txt, "a", encoding="utf-8") as arquivo:
            arquivo.writelines([self._formatar_linha(registro)])
        self.registros.append(registro)

    def consultar(self) -> list[RegistroColonia]:
        """Retorna uma copia da lista de registros carregados."""
        return list(self.registros)

    def atualizar_revisao(self, id_registro: int, status: str) -> bool:
        """Atualiza a revisao humana de um registro ja existente."""
        status_normalizado = status.strip().upper()
        if status_normalizado not in REVISOES_VALIDAS:
            raise ValueError("status de revisão inválido")
        for registro in self.registros:
            if registro.id_registro == id_registro:
                registro.revisao_humana = status_normalizado
                return True
        return False

    @staticmethod
    def _formatar_linha(registro: RegistroColonia) -> str:
        """Monta a linha do arquivo texto a partir de um registro.

        O separador e removido dos campos livres para que uma descricao
        digitada pelo operador nunca quebre o formato do arquivo.
        """
        campos = [
            str(registro.id_registro),
            registro.data_hora,
            registro.categoria.replace(SEPARADOR, "/"),
            registro.descricao.replace(SEPARADOR, "/"),
            str(registro.falha),
            str(registro.critico),
        ]
        return SEPARADOR.join(campos) + "\n"

    def carregar_txt(self) -> None:
        """Le o arquivo texto linha a linha e ignora linhas invalidas.

        Demonstra a leitura com ``open()`` em modo ``"r"`` e o metodo
        ``readlines()``, que devolve todas as linhas em uma lista.
        """
        self.registros = []
        if not self.arquivo_txt.exists():
            return
        with open(self.arquivo_txt, "r", encoding="utf-8") as arquivo:
            linhas = arquivo.readlines()
        for numero, linha in enumerate(linhas, start=1):
            linha = linha.strip()
            if not linha:
                continue
            partes = linha.split(SEPARADOR)
            if len(partes) != 6:
                self.avisos_leitura.append(
                    f"Linha {numero} ignorada: formato inválido."
                )
                continue
            try:
                self.registros.append(
                    RegistroColonia(
                        id_registro=int(partes[0].strip()),
                        data_hora=partes[1].strip(),
                        categoria=partes[2].strip(),
                        descricao=partes[3].strip(),
                        falha=self._ler_booleano(partes[4]),
                        critico=self._ler_booleano(partes[5]),
                    )
                )
            except ValueError:
                self.avisos_leitura.append(f"Linha {numero} ignorada: dados inválidos.")

    def ler_txt_bruto(self) -> str:
        """Devolve o conteudo integral do arquivo texto.

        Demonstra o metodo ``read()``, util para exibir o log completo.
        """
        if not self.arquivo_txt.exists():
            return ""
        with open(self.arquivo_txt, "r", encoding="utf-8") as arquivo:
            return arquivo.read()

    def primeira_linha_txt(self) -> str:
        """Devolve apenas a primeira linha do log.

        Demonstra o metodo ``readline()``, que le uma linha por chamada.
        """
        if not self.arquivo_txt.exists():
            return ""
        with open(self.arquivo_txt, "r", encoding="utf-8") as arquivo:
            return arquivo.readline().strip()

    @staticmethod
    def _ler_booleano(valor: str) -> bool:
        """Converte o texto gravado no arquivo de volta para booleano."""
        valor_normalizado = valor.strip().lower()
        if valor_normalizado == "true":
            return True
        if valor_normalizado == "false":
            return False
        raise ValueError("valor booleano invalido")

    def reescrever_txt(self) -> None:
        """Regrava o arquivo texto inteiro a partir dos registros em memoria.

        Usa o modo ``"w"``, que reinicia o arquivo, e ``writelines()`` para
        gravar todas as linhas de uma vez. E o caminho usado quando a fonte
        primaria foi o JSON e o log precisa ser sincronizado.
        """
        self.arquivo_txt.parent.mkdir(parents=True, exist_ok=True)
        linhas = [self._formatar_linha(registro) for registro in self.registros]
        with open(self.arquivo_txt, "w", encoding="utf-8") as arquivo:
            arquivo.writelines(linhas)

    def salvar_json(self, rede: RedeInfraestrutura | None = None) -> None:
        """Salva o documento JSON usando substituicao atomica.

        O dicionario e escrito primeiro em um arquivo temporario e so depois
        substitui o arquivo final. Assim uma falha no meio da gravacao nao
        deixa um JSON pela metade no disco.
        """
        documento: dict[str, Any] = {
            "sistema": "Núcleo Cognitivo da Aurora Siger (NCAS)",
            "atualizado_em": datetime.now().astimezone().isoformat(),
            "total_registros": len(self.registros),
            "registros": [asdict(registro) for registro in self.registros],
        }
        if rede is not None:
            documento["infraestrutura_ncas"] = resumo_rede(rede)

        self.arquivo_json.parent.mkdir(parents=True, exist_ok=True)
        temporario: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.arquivo_json.parent,
                prefix=f"{self.arquivo_json.stem}_",
                suffix=".tmp",
                delete=False,
            ) as arquivo:
                temporario = arquivo.name
                json.dump(documento, arquivo, ensure_ascii=False, indent=4)
                arquivo.write("\n")
            Path(temporario).replace(self.arquivo_json)
        finally:
            if temporario is not None and Path(temporario).exists():
                Path(temporario).unlink()

    def carregar_json(self) -> dict[str, Any] | None:
        """Le e valida o JSON salvo, sem perder os dados ja carregados em erro."""
        if not self.arquivo_json.exists():
            return None
        with open(self.arquivo_json, "r", encoding="utf-8") as arquivo:
            documento = json.load(arquivo)
        if not isinstance(documento, dict):
            raise ValueError("o documento JSON deve ser um objeto")
        registros = documento.get("registros", [])
        if not isinstance(registros, list):
            raise ValueError("o campo registros deve ser uma lista")

        novos_registros = [
            self._registro_de_dicionario(item, numero)
            for numero, item in enumerate(registros, start=1)
        ]
        self.registros = novos_registros
        return documento

    @staticmethod
    def _registro_de_dicionario(item: Any, numero: int) -> RegistroColonia:
        """Valida um item do JSON e o converte em RegistroColonia."""
        campos_obrigatorios = {
            "id_registro",
            "data_hora",
            "categoria",
            "descricao",
            "falha",
            "critico",
        }
        campos_opcionais = {"modulo_id", "impacto", "recomendacao", "revisao_humana"}

        if not isinstance(item, dict):
            raise ValueError(f"registro {numero} deve ser um objeto")
        if not campos_obrigatorios.issubset(item) or set(item) - (
            campos_obrigatorios | campos_opcionais
        ):
            raise ValueError(f"registro {numero} possui campos inválidos")
        if (
            not isinstance(item["id_registro"], int)
            or isinstance(item["id_registro"], bool)
            or not isinstance(item["data_hora"], str)
            or not isinstance(item["categoria"], str)
            or not isinstance(item["descricao"], str)
            or not isinstance(item["falha"], bool)
            or not isinstance(item["critico"], bool)
        ):
            raise ValueError(f"registro {numero} possui tipos inválidos")
        if item.get("modulo_id") is not None and not isinstance(item["modulo_id"], str):
            raise ValueError(f"registro {numero} possui tipos inválidos")
        if "impacto" in item and (
            not isinstance(item["impacto"], list)
            or not all(isinstance(modulo_id, str) for modulo_id in item["impacto"])
        ):
            raise ValueError(f"registro {numero} possui tipos inválidos")
        if "recomendacao" in item and not isinstance(item["recomendacao"], str):
            raise ValueError(f"registro {numero} possui tipos inválidos")
        if "revisao_humana" in item and not isinstance(item["revisao_humana"], str):
            raise ValueError(f"registro {numero} possui tipos inválidos")

        dados_registro = dict(item)
        if "impacto" in dados_registro:
            dados_registro["impacto"] = tuple(dados_registro["impacto"])
        return RegistroColonia(**dados_registro)
