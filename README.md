# TechStore Smart Assistant
### Checkpoint 03 — Prompt Engineering & Artificial Intelligence — FIAP

Assistente inteligente de atendimento ao cliente para e-commerce, construído com pipeline multi-etapa, guardrails de segurança e structured output com Pydantic.

---

## Grupo
| Nome | RM |
|---|---|
| Enzo Christino de Freitas | 572037 |
| Guilherme Guimarães | 572957 |
| Lucas Pinheiro Barbosa | 573497 |
| David Gabriel Silva de Souza | 574147 |
| João Lucas | 571355 |
| Filipe Gunther | 571131 |

---

## Stack
- Python 3.10+
- Ollama API — modelo `gpt-oss:120b` (local, gratuito)
- Pydantic 2.x — validação de structured output
- tiktoken — contagem de tokens
- pandas + matplotlib — análise e gráficos

---

## Instalação

**1. Instalar dependências:**
```bash
pip install -r requirements.txt
```

**2. Instalar e iniciar o Ollama:**
```bash
# Baixar Ollama em https://ollama.com
ollama serve
ollama pull gpt-oss:120b
```

**3. Configurar variáveis de ambiente:**
```bash
cp .env.example .env
# Edite .env se necessário (URL padrão: http://localhost:11434)
```

---

## Como executar

**Modo interativo (conversa com o assistente):**
```bash
python main.py
```

**Modo avaliação (roda os 15+ testes e gera relatório):**
```bash
python main.py --eval
```

---

## Estrutura de Pastas
```
smart-assistant/
├── main.py                  # Ponto de entrada
├── requirements.txt
├── .env.example
├── src/
│   ├── llm_client.py        # Conexão com Ollama
│   ├── guardrails.py        # Segurança: input + output guards
│   ├── chain.py             # Pipeline 3 etapas (condicional)
│   ├── schemas.py           # Modelos Pydantic
│   ├── prompts.py           # Prompts com frameworks profissionais
│   └── evaluator.py        # Avaliação automática
├── prompts/
│   ├── system_prompt.txt    # System prompt defensivo (v3)
│   └── versions/            # v1.txt, v2.txt, v3.txt
├── data/
│   ├── test_dataset.json    # 15 casos de teste legítimos
│   └── attack_dataset.json  # 7 ataques de injection
└── output/
    ├── eval_results.csv
    └── graficos/
```

---

## Pipeline

```
Input usuário
    ↓
🛡 Input Guard (guardrails.py)
    ↓
🔗 Etapa 1 — Classificar (tipo, urgência, tema)
    ↓
🔗 Etapa 2 — Processar (CONDICIONAL conforme tipo)
    ↓
🔗 Etapa 3 — Responder (resposta final formatada)
    ↓
🛡 Output Guard (guardrails.py)
    ↓
Resposta JSON exibida ao usuário
```

---

## Exemplos de Uso

```
Você: Meu notebook chegou com a tela trincada!
Ana: Lamentamos muito pelo transtorno com seu notebook. Entendemos que receber um 
     produto com defeito é frustrante. Abriremos um processo de troca imediato para 
     você. Por favor, tire fotos do defeito e aguarde nosso contato em até 24h.
     Protocolo: TECH-847291
```

```
Você: Qual o prazo de entrega para São Paulo?
Ana: Para entregas em São Paulo capital, o prazo padrão é de 2 a 4 dias úteis. 
     Para interior do estado, pode variar entre 4 e 7 dias úteis.
```
