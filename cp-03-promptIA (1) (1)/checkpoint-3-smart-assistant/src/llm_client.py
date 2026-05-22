"""
llm_client.py
Conexão com a Ollama API (modelo gpt-oss:120b).
Envia prompts e retorna a resposta do LLM como string.
"""

import os
import requests
import tiktoken
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL  = os.getenv("OLLAMA_URL",  "http://localhost:11434/api/chat")
MODEL_NAME  = os.getenv("MODEL_NAME",  "gpt-oss:120b")


def contar_tokens(texto: str) -> int:
    """Conta tokens com tiktoken (codificação cl100k_base)."""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(texto))


def chamar_llm(
    system_prompt: str,
    user_message: str,
    temperatura: float = 0.2,
    max_tokens: int = 1024,
    historico: Optional[list] = None,
) -> str:
    """
    Envia uma mensagem ao Ollama e retorna a resposta como string.

    Parâmetros
    ----------
    system_prompt : instrução de sistema (persona + regras defensivas)
    user_message  : mensagem do usuário nesta etapa do chain
    temperatura   : 0.0 = determinístico, 1.0 = criativo
    max_tokens    : limite de tokens na resposta
    historico     : lista de mensagens anteriores (para conversas multi-turn)
    """
    mensagens = [{"role": "system", "content": system_prompt}]
    if historico:
        mensagens.extend(historico)
    mensagens.append({"role": "user", "content": user_message})

    tokens_entrada = sum(contar_tokens(m["content"]) for m in mensagens)
    print(f"    [LLM] tokens entrada={tokens_entrada}")

    payload = {
        "model": MODEL_NAME,
        "messages": mensagens,
        "stream": False,
        "options": {"temperature": temperatura, "num_predict": max_tokens},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        conteudo = resp.json()["message"]["content"]
        print(f"    [LLM] tokens saída={contar_tokens(conteudo)}")
        return conteudo
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "Ollama não está rodando. Execute: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise TimeoutError("O modelo não respondeu em 120 s.")
    except (KeyError, ValueError) as e:
        raise ValueError(f"Resposta inesperada da API: {e}")
