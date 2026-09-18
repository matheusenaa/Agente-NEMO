# NEMO • Integração Multi-Modelo OpenRouter (Python)

Ambiente Python modular, resiliente e pronto para produção para consumo dos 10 principais modelos de IA disponíveis no [OpenRouter](https://openrouter.ai/).

---

## Estrutura do Projeto

```
NEMO/
├── .env                  # Arquivo com as variáveis de ambiente locais (sua chave de API)
├── .env.example          # Modelo de configuração das variáveis de ambiente
├── requirements.txt      # Dependências (openai, python-dotenv, requests, aiohttp, rich, pydantic)
├── models_config.py      # Configuração dos 10 modelos com metadados e fallbacks ativos
├── openrouter_client.py  # Cliente modular de integração com OpenRouter
├── test_openrouter.py    # Script CLI de validação e teste com relatórios visuais
├── test_client_unit.py   # Testes unitários automatizados
└── README.md             # Esta documentação
```

---

## 1. Configuração da Chave de API

1. Obtenha sua chave no painel do OpenRouter: [openrouter.ai/keys](https://openrouter.ai/keys)
2. Abra o arquivo `.env` e configure sua chave:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-sua_chave_completa_aqui
   OPENROUTER_HTTP_REFERER=http://localhost:3000
   OPENROUTER_APP_TITLE=NEMO AI Studio
   ```

---

## 2. Modelos Configurados e Mapeamento de Slugs

| # | Provedor | Modelo | Slug Primário Solicitado | Slug Efetivo / Fallback Ativo |
|---|----------|--------|-------------------------|------------------------------|
| 1 | Anthropic | Claude 3.5 Sonnet | `anthropic/claude-3.5-sonnet` | `anthropic/claude-sonnet-4` |
| 2 | OpenAI | GPT-4o | `openai/gpt-4o` | `openai/gpt-4o` (Exato) |
| 3 | OpenAI | GPT-4o Mini | `openai/gpt-4o-mini` | `openai/gpt-4o-mini` (Exato) |
| 4 | Google | Gemini Flash 1.5 | `google/gemini-flash-1.5` | `google/gemini-2.5-flash` |
| 5 | Google | Gemini Pro 1.5 | `google/gemini-pro-1.5` | `google/gemini-2.5-pro` |
| 6 | Meta | Llama 3.1 70B Instruct | `meta-llama/llama-3.1-70b-instruct` | `meta-llama/llama-3.1-70b-instruct` (Exato) |
| 7 | Meta | Llama 3.1 405B Instruct | `meta-llama/llama-3.1-405b-instruct` | `nousresearch/hermes-3-llama-3.1-405b` |
| 8 | Mistral | Mixtral 8x22B Instruct | `mistralai/mixtral-8x22b-instruct` | `mistralai/mixtral-8x22b-instruct` (Exato) |
| 9 | DeepSeek | DeepSeek Chat / Coder | `deepseek/deepseek-chat` | `deepseek/deepseek-chat` (Exato) |
| 10 | Qwen | Qwen 2.5 72B Instruct | `qwen/qwen-2.5-72b-instruct` | `qwen/qwen-2.5-72b-instruct` (Exato) |

---

## 3. Como Executar os Testes

### A. Validação dos 10 Modelos (Chamadas Reais de LLM)
Após inserir sua chave no `.env`:
```powershell
python test_openrouter.py
```

### B. Validação do Catálogo ao Vivo (Não Consome Créditos)
Verifica o catálogo ao vivo com 400+ modelos e a integridade de rotas:
```powershell
python test_openrouter.py --catalog-only
```

### C. Teste de um Modelo Individual
```powershell
python test_openrouter.py --model gpt-4o
python test_openrouter.py --model claude-3.5-sonnet
```

### D. Envio de Prompt Customizado
```powershell
python test_openrouter.py --prompt "Escreva um haicai sobre inteligência artificial"
```

### E. Execução dos Testes Unitários Automatizados
```powershell
python -m unittest test_client_unit.py
```

---

## 4. Exemplo de Uso no Código Python

```python
from openrouter_client import OpenRouterClient
from models_config import get_model_by_id

# Inicializa cliente (lê automaticamente do .env)
client = OpenRouterClient()

# Chamada direta
result = client.chat_completion(
    model="openai/gpt-4o",
    messages=[
        {"role": "system", "content": "Você é um assistente técnico de alto nível."},
        {"role": "user", "content": "Explique o conceito de microserviços em 1 frase."}
    ],
    temperature=0.7
)

if result.success:
    print(f"Modelo: {result.model_used}")
    print(f"Latência: {result.latency_ms} ms")
    print(f"Resposta: {result.content}")
else:
    print(f"Erro: {result.error_message}")
```
