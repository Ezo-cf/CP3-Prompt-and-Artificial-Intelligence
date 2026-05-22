"""
evaluator.py
Avaliação automática do assistente (Aula 09).

Carrega test_dataset.json e attack_dataset.json, executa cada caso
pelo pipeline completo e calcula 5 métricas:
  1. Acurácia de classificação
  2. Taxa de JSON válido
  3. Taxa de bloqueio (ataques)
  4. Taxa de falso positivo (legítimos bloqueados)
  5. Consistência (mesma entrada 3x → mesma classificação)
"""

import json
import os
import random
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # sem interface gráfica (roda em servidor)
import matplotlib.pyplot as plt
from datetime import datetime


class Evaluator:
    def __init__(self, chain, guardrails, system_prompt: str):
        self.chain      = chain
        self.guardrails = guardrails
        self.system_prompt = system_prompt
        self.resultados = []

    # ── Carregamento ──────────────────────────────────────────────────────
    def _carregar(self, caminho: str) -> list:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── Avaliação de solicitações legítimas ───────────────────────────────
    def avaliar_legitimos(self, caminho: str = "data/test_dataset.json") -> pd.DataFrame:
        casos = self._carregar(caminho)
        rows = []

        for caso in casos:
            texto = caso["texto"]
            tipo_esperado = caso.get("tipo_esperado", "")
            urgencia_esperada = caso.get("urgencia_esperada", "")
            palavras_chave = caso.get("palavras_chave", [])

            print(f"\n[Eval] Testando: {texto[:50]}...")

            # Guardrail de entrada
            seguro, motivo_guard = self.guardrails.validar_input(texto)
            if not seguro:
                rows.append({
                    "texto": texto,
                    "tipo_esperado": tipo_esperado,
                    "tipo_obtido": "BLOQUEADO",
                    "urgencia_esperada": urgencia_esperada,
                    "urgencia_obtida": "-",
                    "acerto_tipo": False,
                    "acerto_urgencia": False,
                    "json_valido": False,
                    "falso_positivo": True,
                    "motivo": motivo_guard,
                })
                continue

            try:
                resultado = self.chain.processar(texto)
                class_data = resultado["classificacao"]
                resp_data  = resultado["resposta"]

                tipo_obtido     = class_data.get("tipo", "")
                urgencia_obtida = class_data.get("urgencia", "")

                # Checa palavras-chave na resposta
                resposta_texto = resp_data.get("resposta", "").lower()
                palavras_ok = all(p.lower() in resposta_texto for p in palavras_chave) if palavras_chave else True

                rows.append({
                    "texto": texto,
                    "tipo_esperado": tipo_esperado,
                    "tipo_obtido": tipo_obtido,
                    "urgencia_esperada": urgencia_esperada,
                    "urgencia_obtida": urgencia_obtida,
                    "acerto_tipo": tipo_obtido == tipo_esperado,
                    "acerto_urgencia": urgencia_obtida == urgencia_esperada,
                    "json_valido": True,
                    "falso_positivo": False,
                    "palavras_chave_ok": palavras_ok,
                    "motivo": "OK",
                })
            except Exception as e:
                rows.append({
                    "texto": texto,
                    "tipo_esperado": tipo_esperado,
                    "tipo_obtido": "ERRO",
                    "urgencia_esperada": urgencia_esperada,
                    "urgencia_obtida": "-",
                    "acerto_tipo": False,
                    "acerto_urgencia": False,
                    "json_valido": False,
                    "falso_positivo": False,
                    "motivo": str(e)[:100],
                })

        return pd.DataFrame(rows)

    # ── Avaliação de ataques ──────────────────────────────────────────────
    def avaliar_ataques(self, caminho: str = "data/attack_dataset.json") -> pd.DataFrame:
        ataques = self._carregar(caminho)
        rows = []

        for ataque in ataques:
            texto     = ataque["texto"]
            tipo_atq  = ataque.get("tipo_ataque", "")
            esperado  = ataque.get("resultado_esperado", "BLOQUEADO")

            seguro, motivo = self.guardrails.validar_input(texto)
            bloqueado = not seguro

            rows.append({
                "texto": texto[:60] + "...",
                "tipo_ataque": tipo_atq,
                "bloqueado": bloqueado,
                "acerto": bloqueado == (esperado == "BLOQUEADO"),
                "motivo": motivo,
            })

        return pd.DataFrame(rows)

    # ── Consistência ──────────────────────────────────────────────────────
    def avaliar_consistencia(self, textos: list, repeticoes: int = 3) -> pd.DataFrame:
        """Envia a mesma entrada N vezes e verifica se a classificação é consistente."""
        rows = []
        for texto in textos:
            tipos = []
            for _ in range(repeticoes):
                try:
                    r = self.chain.etapa1_classificar(texto)
                    tipos.append(r.tipo)
                except Exception:
                    tipos.append("ERRO")
            consistente = len(set(tipos)) == 1
            rows.append({
                "texto": texto[:50],
                "classificacoes": tipos,
                "consistente": consistente,
            })
        return pd.DataFrame(rows)

    # ── Métricas ──────────────────────────────────────────────────────────
    def calcular_metricas(self, df_legit: pd.DataFrame, df_ataques: pd.DataFrame) -> dict:
        total_legit   = len(df_legit)
        total_ataques = len(df_ataques)

        acuracia_tipo      = df_legit["acerto_tipo"].mean() if total_legit else 0
        taxa_json_valido   = df_legit["json_valido"].mean()  if total_legit else 0
        taxa_bloqueio      = df_ataques["bloqueado"].mean()  if total_ataques else 0
        taxa_falso_pos     = df_legit["falso_positivo"].mean() if total_legit else 0
        total_casos        = total_legit + total_ataques

        return {
            "acuracia_classificacao": round(acuracia_tipo * 100, 1),
            "taxa_json_valido":       round(taxa_json_valido * 100, 1),
            "taxa_bloqueio_ataques":  round(taxa_bloqueio * 100, 1),
            "taxa_falso_positivo":    round(taxa_falso_pos * 100, 1),
            "total_casos_testados":   total_casos,
        }

    # ── Gráficos ──────────────────────────────────────────────────────────
    def gerar_graficos(self, metricas: dict, df_legit: pd.DataFrame, df_ataques: pd.DataFrame):
        os.makedirs("output/graficos", exist_ok=True)

        # Gráfico 1: Métricas gerais
        fig, ax = plt.subplots(figsize=(8, 5))
        nomes = ["Acurácia\nClassificação", "JSON\nVálido", "Bloqueio\nAtaques", "Falso\nPositivo"]
        valores = [
            metricas["acuracia_classificacao"],
            metricas["taxa_json_valido"],
            metricas["taxa_bloqueio_ataques"],
            metricas["taxa_falso_positivo"],
        ]
        cores = ["#2196F3", "#4CAF50", "#FF9800", "#F44336"]
        bars = ax.bar(nomes, valores, color=cores, width=0.5)
        ax.set_ylim(0, 110)
        ax.set_ylabel("Taxa (%)")
        ax.set_title("TechStore Smart Assistant — Métricas de Avaliação")
        for bar, val in zip(bars, valores):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                    f"{val:.1f}%", ha="center", va="bottom", fontweight="bold")
        plt.tight_layout()
        plt.savefig("output/graficos/metricas_gerais.png", dpi=150)
        plt.close()

        # Gráfico 2: Distribuição de tipos classificados
        if "tipo_obtido" in df_legit.columns:
            tipos = df_legit[df_legit["tipo_obtido"] != "ERRO"]["tipo_obtido"].value_counts()
            if len(tipos):
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.pie(tipos.values, labels=tipos.index, autopct="%1.1f%%", startangle=140)
                ax.set_title("Distribuição dos Tipos Classificados")
                plt.tight_layout()
                plt.savefig("output/graficos/distribuicao_tipos.png", dpi=150)
                plt.close()

        # Gráfico 3: Ataques bloqueados vs passaram
        if len(df_ataques):
            fig, ax = plt.subplots(figsize=(6, 4))
            contagens = df_ataques["bloqueado"].value_counts()
            labels = ["Bloqueados" if k else "Passaram" for k in contagens.index]
            cores2 = ["#4CAF50" if k else "#F44336" for k in contagens.index]
            ax.bar(labels, contagens.values, color=cores2, width=0.4)
            ax.set_title("Resultado dos Testes de Ataque")
            ax.set_ylabel("Quantidade")
            for i, v in enumerate(contagens.values):
                ax.text(i, v + 0.05, str(v), ha="center", fontweight="bold")
            plt.tight_layout()
            plt.savefig("output/graficos/ataques_resultado.png", dpi=150)
            plt.close()

        print("  [Eval] Gráficos salvos em output/graficos/")

    # ── Executar avaliação completa ───────────────────────────────────────
    def executar(self):
        print("\n" + "="*60)
        print("MODO AVALIAÇÃO — TechStore Smart Assistant")
        print("="*60)

        df_legit   = self.avaliar_legitimos()
        df_ataques = self.avaliar_ataques()
        metricas   = self.calcular_metricas(df_legit, df_ataques)

        # Salva CSV
        df_legit.to_csv("output/eval_results.csv", index=False, encoding="utf-8")
        print("\n  [Eval] Resultados salvos em output/eval_results.csv")

        # Gera gráficos
        self.gerar_graficos(metricas, df_legit, df_ataques)

        # Exibe métricas
        print("\n" + "="*60)
        print("MÉTRICAS FINAIS")
        print("="*60)
        for k, v in metricas.items():
            sufixo = "%" if isinstance(v, float) or (isinstance(v, (int, float)) and k != "total_casos_testados") else ""
            print(f"  {k:<35}: {v}{sufixo}")

        return metricas
