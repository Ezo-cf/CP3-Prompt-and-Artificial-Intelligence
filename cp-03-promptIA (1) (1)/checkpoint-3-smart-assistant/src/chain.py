"""
chain.py
Pipeline multi-etapa (Aula 09) com lógica condicional.

Fluxo:
  Input → Etapa1 (classificar) → Etapa2 (processar, varia por tipo) → Etapa3 (responder)

A Etapa 2 usa um prompt DIFERENTE para cada tipo retornado pela Etapa 1:
  reclamacao → extrai produto + defeito
  duvida     → gera resposta informativa
  elogio     → registra e agradece
  devolucao  → extrai dados de devolução
  sugestao   → avalia viabilidade
"""

import json
import re
import random
from pydantic import ValidationError

from src.llm_client import chamar_llm
from src.schemas import ClassificacaoSchema, ProcessamentoSchema, RespostaSchema
from src.prompts import prompt_etapa1, prompt_etapa2, prompt_etapa3


def _extrair_json(texto: str) -> dict:
    """
    Extrai o primeiro bloco JSON de uma string.
    Usado para lidar com respostas que incluem texto extra além do JSON.
    """
    # Tenta parse direto primeiro
    try:
        return json.loads(texto.strip())
    except json.JSONDecodeError:
        pass

    # Tenta encontrar bloco JSON com regex
    match = re.search(r"\{[\s\S]*\}", texto)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Não foi possível extrair JSON da resposta:\n{texto[:300]}")


def _chamar_com_retry(system_prompt, user_prompt, schema_class, tentativas=3):
    """
    Chama o LLM e valida com Pydantic. Faz retry se a validação falhar.
    """
    for tentativa in range(1, tentativas + 1):
        print(f"  [Chain] Tentativa {tentativa}/{tentativas}")
        try:
            resposta_raw = chamar_llm(system_prompt, user_prompt)
            dados = _extrair_json(resposta_raw)
            return schema_class(**dados)
        except (ValidationError, ValueError) as e:
            print(f"  [Chain] Falha na validação: {e}")
            if tentativa == tentativas:
                raise RuntimeError(
                    f"Falha após {tentativas} tentativas. Último erro: {e}"
                )


class AssistantChain:
    """
    Pipeline principal do TechStore Smart Assistant.
    Cada método corresponde a uma etapa do chain.
    """

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    # ── ETAPA 1: Classificar ──────────────────────────────────────────────
    def etapa1_classificar(self, texto_usuario: str) -> ClassificacaoSchema:
        """
        Recebe texto livre do usuário.
        Retorna JSON com tipo, urgência, tema e confiança.
        """
        print("\n[Etapa 1] Classificando solicitação...")
        user_prompt = prompt_etapa1(texto_usuario)
        resultado = _chamar_com_retry(
            self.system_prompt,
            user_prompt,
            ClassificacaoSchema
        )
        print(f"  → tipo={resultado.tipo} | urgencia={resultado.urgencia} | confianca={resultado.confianca_classificacao}")
        return resultado

    # ── ETAPA 2: Processar (condicional) ──────────────────────────────────
    def etapa2_processar(
        self,
        classificacao: ClassificacaoSchema,
        texto_original: str,
    ) -> ProcessamentoSchema:
        """
        Recebe o resultado da Etapa 1 + texto original.
        O prompt usado VARIA conforme o tipo classificado — isso é o chain condicional.
        """
        print(f"\n[Etapa 2] Processando como '{classificacao.tipo}'...")
        user_prompt = prompt_etapa2(
            tipo=classificacao.tipo,
            urgencia=classificacao.urgencia,
            tema=classificacao.tema,
            texto=texto_original,
        )
        resultado = _chamar_com_retry(
            self.system_prompt,
            user_prompt,
            ProcessamentoSchema
        )
        print(f"  → sentimento={resultado.sentimento} | acao={resultado.acao_recomendada[:40]}")
        return resultado

    # ── ETAPA 3: Responder ────────────────────────────────────────────────
    def etapa3_responder(
        self,
        classificacao: ClassificacaoSchema,
        processamento: ProcessamentoSchema,
    ) -> RespostaSchema:
        """
        Recebe os resultados das etapas 1 e 2.
        Gera a resposta final formatada para o usuário.
        """
        print("\n[Etapa 3] Gerando resposta final...")
        user_prompt = prompt_etapa3(
            tipo=classificacao.tipo,
            urgencia=classificacao.urgencia,
            analise=processamento.analise,
            acao_recomendada=processamento.acao_recomendada,
            sentimento=processamento.sentimento or "neutro",
        )
        resultado = _chamar_com_retry(
            self.system_prompt,
            user_prompt,
            RespostaSchema
        )
        print(f"  → confianca={resultado.confianca}")
        return resultado

    # ── Pipeline completo ─────────────────────────────────────────────────
    def processar(self, texto_usuario: str) -> dict:
        """
        Executa as 3 etapas em sequência e retorna um dicionário com tudo.
        """
        etapa1 = self.etapa1_classificar(texto_usuario)
        etapa2 = self.etapa2_processar(etapa1, texto_usuario)
        etapa3 = self.etapa3_responder(etapa1, etapa2)

        return {
            "classificacao": etapa1.model_dump(),
            "processamento": etapa2.model_dump(),
            "resposta":      etapa3.model_dump(),
        }
