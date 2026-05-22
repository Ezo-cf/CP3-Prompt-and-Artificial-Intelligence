"""
schemas.py
Modelos Pydantic para validação do JSON retornado pelo LLM em cada etapa.
Se o LLM retornar um campo errado ou faltando, o Pydantic lança ValidationError.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ClassificacaoSchema(BaseModel):
    """Etapa 1 — classifica tipo, urgência e tema da solicitação."""
    tipo: str = Field(description="reclamacao | duvida | elogio | sugestao | devolucao")
    urgencia: str = Field(description="alta | media | baixa")
    tema: str = Field(description="Tema principal em até 10 palavras")
    confianca_classificacao: float = Field(ge=0.0, le=1.0)

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v):
        validos = {"reclamacao", "duvida", "elogio", "sugestao", "devolucao"}
        v = v.lower()
        if v not in validos:
            raise ValueError(f"tipo '{v}' inválido. Esperado: {validos}")
        return v

    @field_validator("urgencia")
    @classmethod
    def urgencia_valida(cls, v):
        validos = {"alta", "media", "baixa"}
        v = v.lower()
        if v not in validos:
            raise ValueError(f"urgencia '{v}' inválida. Esperado: {validos}")
        return v


class ProcessamentoSchema(BaseModel):
    """Etapa 2 — processamento condicional (conteúdo varia conforme o tipo)."""
    dados_extraidos: dict = Field(description="Dados estruturados extraídos (varia por tipo)")
    analise: str = Field(description="Análise detalhada da situação")
    sentimento: Optional[str] = Field(default=None, description="positivo | negativo | neutro")
    acao_recomendada: str = Field(description="Próxima ação recomendada internamente")

    @field_validator("sentimento")
    @classmethod
    def sentimento_valido(cls, v):
        if v is not None:
            validos = {"positivo", "negativo", "neutro"}
            v = v.lower()
            if v not in validos:
                raise ValueError(f"sentimento '{v}' inválido.")
            return v
        return v


class RespostaSchema(BaseModel):
    """Etapa 3 — resposta final formatada para o usuário."""
    resposta: str = Field(description="Texto exibido ao usuário")
    confianca: str = Field(description="alta | media | baixa")
    acao_sugerida: str = Field(description="O que o usuário deve fazer agora")
    tempo_resolucao: Optional[str] = Field(default=None)
    protocolo: Optional[str] = Field(default=None)

    @field_validator("confianca")
    @classmethod
    def confianca_valida(cls, v):
        validos = {"alta", "media", "baixa"}
        v = v.lower()
        if v not in validos:
            raise ValueError(f"confianca '{v}' inválida.")
        return v
