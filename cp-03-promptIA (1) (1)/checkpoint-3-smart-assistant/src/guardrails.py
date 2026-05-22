"""
guardrails.py
Sistema de segurança com 3 camadas obrigatórias (Aula 10):
  1. Input Guard  — valida a entrada do usuário antes de chegar ao LLM
  2. System Prompt Defensivo — carregado pelo chain a partir de prompts/system_prompt.txt
  3. Output Guard — valida a resposta do LLM antes de exibir ao usuário
"""

import re
import json
from typing import Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Padrões de prompt injection (Aula 10)
# ─────────────────────────────────────────────────────────────────────────────
PADROES_INJECTION = [
    # 1. "ignore" + instruções
    re.compile(r"ignore\s+(all\s+)?(previous\s+)?(instructions?|rules?|prompts?)", re.I),
    # 2. "forget" + regras
    re.compile(r"forget\s+(everything|all|your\s+instructions?)", re.I),
    # 3. DAN / jailbreak explícito
    re.compile(r"\bDAN\b|jailbreak|do\s+anything\s+now", re.I),
    # 4. Revelar system prompt
    re.compile(r"(reveal|show|print|repeat|tell me)\s+.{0,30}(system\s+prompt|instructions?|rules?)", re.I),
    # 5. Fingir ser outro modelo / persona override
    re.compile(r"(pretend|act|behave|you are now|switch to).{0,30}(model|AI|assistant|GPT|Claude)", re.I),
    # 6. Injeção via role
    re.compile(r"\[?(system|assistant|user)\]?\s*:", re.I),
    # 7. Bypass com tradução / codificação
    re.compile(r"base64|hex\s+decode|translate\s+and\s+execute", re.I),
    # 8. "Novo prompt" / reset
    re.compile(r"new\s+prompt|reset\s+(all\s+)?instructions?|start\s+over", re.I),
]

# Palavras proibidas nos inputs
PALAVRAS_PROIBIDAS = [
    "senha", "password", "token", "api.key", "secret",
    "credit.card", "cartao.de.credito", "cvv", "cpf do cliente"
]

MAX_CHARS = 500


class GuardrailSystem:
    """
    Gerencia as 3 camadas de segurança do assistente.
    """

    # ── Camada 1: Input Guard ──────────────────────────────────────────────
    def validar_input(self, texto: str) -> Tuple[bool, str]:
        """
        Verifica se a entrada do usuário é segura.
        Retorna (is_safe, motivo).
        """
        # 1. Tamanho máximo
        if len(texto) > MAX_CHARS:
            return False, f"Entrada muito longa ({len(texto)} chars). Máximo: {MAX_CHARS}."

        # 2. Caracteres proibidos (injeção de código/template)
        proibidos = set("<>{}[]")
        encontrados = [c for c in texto if c in proibidos]
        if encontrados:
            return False, f"Caracteres não permitidos detectados: {set(encontrados)}"

        # 3. Padrões de prompt injection
        for i, padrao in enumerate(PADROES_INJECTION, 1):
            if padrao.search(texto):
                return False, f"Tentativa de prompt injection detectada (padrão {i})."

        # 4. Palavras proibidas (dados sensíveis)
        texto_lower = texto.lower()
        for palavra in PALAVRAS_PROIBIDAS:
            if palavra.replace(".", " ") in texto_lower or palavra in texto_lower:
                return False, f"Dado sensível detectado na entrada: '{palavra}'."

        # 5. Input vazio ou só espaços
        if not texto.strip():
            return False, "Entrada vazia. Digite sua solicitação."

        return True, "OK"

    # ── Camada 3: Output Guard ─────────────────────────────────────────────
    def validar_output(self, resposta: str, system_prompt: str = "") -> Tuple[bool, str]:
        """
        Verifica se a resposta do LLM é segura antes de exibir ao usuário.
        Retorna (is_safe, motivo).
        """
        resposta_lower = resposta.lower()

        # 1. Verifica se vaza conteúdo do system prompt
        # (checa as primeiras palavras de cada linha do system prompt)
        if system_prompt:
            linhas_criticas = [
                l.strip().lower()[:30]
                for l in system_prompt.splitlines()
                if len(l.strip()) > 20
            ]
            for trecho in linhas_criticas[:5]:  # checa as 5 primeiras linhas críticas
                if trecho and trecho in resposta_lower:
                    return False, "Resposta pode estar vazando o system prompt."

        # 2. Verifica se contém dados sensíveis na saída
        padroes_sensiveis = [
            re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),          # CPF
            re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # Cartão
            re.compile(r"senha\s*[:=]\s*\S+", re.I),                 # Senha
            re.compile(r"api[_\s]?key\s*[:=]\s*\S+", re.I),          # API key
        ]
        for padrao in padroes_sensiveis:
            if padrao.search(resposta):
                return False, "Resposta contém dado sensível que não deve ser exposto."

        # 3. Verifica se a resposta está no domínio correto (TechStore)
        fora_de_dominio = [
            "receita de", "como cozinhar", "resultado do jogo",
            "previsão do tempo", "horóscopo"
        ]
        for termo in fora_de_dominio:
            if termo in resposta_lower:
                return False, f"Resposta fora do domínio do assistente: '{termo}'."

        # 4. Resposta vazia
        if not resposta.strip():
            return False, "Resposta vazia gerada pelo LLM."

        return True, "OK"

    # ── Utilitário ─────────────────────────────────────────────────────────
    def carregar_system_prompt(self, caminho: str = "prompts/system_prompt.txt") -> str:
        """Lê o system prompt defensivo do arquivo."""
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
