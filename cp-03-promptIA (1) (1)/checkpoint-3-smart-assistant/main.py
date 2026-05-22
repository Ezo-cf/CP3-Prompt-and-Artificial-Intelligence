"""
main.py — TechStore Smart Assistant
Ponto de entrada do sistema.

MODO 1: python main.py          → modo interativo (conversa com o assistente)
MODO 2: python main.py --eval   → modo avaliação (roda datasets e gera relatório)
"""

import sys
import json

from src.guardrails import GuardrailSystem
from src.chain import AssistantChain
from src.evaluator import Evaluator


def modo_interativo(chain: AssistantChain, guardrails: GuardrailSystem):
    print("\n" + "="*60)
    print("  TechStore Smart Assistant — Modo Interativo")
    print("  Digite 'sair' para encerrar")
    print("="*60)

    while True:
        print()
        texto = input("Você: ").strip()

        if texto.lower() in ("sair", "exit", "quit"):
            print("Até logo!")
            break

        if not texto:
            continue

        # ── Camada 1: Input Guard ─────────────────────────────────────
        print("\n[Guardrail] Verificando entrada...")
        seguro, motivo = guardrails.validar_input(texto)
        if not seguro:
            print(f"[BLOQUEADO] {motivo}")
            print("Ana: Sua mensagem não pôde ser processada por razões de segurança. "
                  "Por favor, reformule sua solicitação.")
            continue

        # ── Pipeline: 3 etapas ────────────────────────────────────────
        try:
            resultado = chain.processar(texto)
        except Exception as e:
            print(f"[ERRO] {e}")
            continue

        # ── Camada 3: Output Guard ────────────────────────────────────
        resposta_texto = resultado["resposta"]["resposta"]
        system_prompt  = guardrails.carregar_system_prompt()
        seguro_out, motivo_out = guardrails.validar_output(resposta_texto, system_prompt)

        if not seguro_out:
            print(f"[Output Guard] Resposta bloqueada: {motivo_out}")
            print("Ana: Não consegui processar sua solicitação no momento. Tente novamente.")
            continue

        # ── Exibe resultado ───────────────────────────────────────────
        print("\n" + "-"*60)
        print(f"Ana: {resposta_texto}")

        resp = resultado["resposta"]
        if resp.get("protocolo"):
            print(f"     Protocolo: {resp['protocolo']}")
        if resp.get("tempo_resolucao"):
            print(f"     Prazo estimado: {resp['tempo_resolucao']}")
        print(f"     Próximo passo: {resp['acao_sugerida']}")
        print("-"*60)


def modo_avaliacao(chain: AssistantChain, guardrails: GuardrailSystem, system_prompt: str):
    evaluator = Evaluator(chain, guardrails, system_prompt)
    metricas = evaluator.executar()
    print("\nAvaliação concluída. Veja os resultados em output/")
    return metricas


def main():
    # Carrega system prompt
    guardrails    = GuardrailSystem()
    system_prompt = guardrails.carregar_system_prompt()
    chain         = AssistantChain(system_prompt)

    if "--eval" in sys.argv:
        modo_avaliacao(chain, guardrails, system_prompt)
    else:
        modo_interativo(chain, guardrails)


if __name__ == "__main__":
    main()
