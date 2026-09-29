# -*- coding: utf-8 -*-
"""
Isolamento do ambiente de testes.

`nemo_server` faz `load_dotenv()` na importaÃ§Ã£o, entÃ£o o `.env` da mÃ¡quina do
desenvolvedor (NEMO_AI_PROVIDER, chaves) entrava no teste e o chat do teste ia
para a API de verdade em vez do mock. Resultado: 19 testes que passam no
`get_client()` mockado comeÃ§aram a falhar conforme o `.env` local mudava â€” o
teste dependia do computador, nÃ£o do cÃ³digo.

Aqui o provedor default do sistema Ã© fixado em `openrouter` ANTES de qualquer
import, que Ã© o contrato dos testes (sem config do usuÃ¡rio => OpenRouter). Os
testes que querem outro provedor pedem explicitamente no request, e os que
testam a precedÃªncia patcham `AI_SERVICE.default_provider`.
"""

import os

os.environ["NEMO_AI_PROVIDER"] = "openrouter"

