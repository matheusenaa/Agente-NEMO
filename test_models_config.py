# -*- coding: utf-8 -*-
"""
Confere os slugs de `models_config.py` contra o catálogo VIVO do OpenRouter.

Regressão real: `deepseek/deepseek-coder` não existe mais. O OpenRouter
responde 400 "not a valid model ID" e, como a cadeia de fallback só reportava
a última mensagem, esse 400 mascarava a causa verdadeira da falha.

O teste é SKIPPED quando não há chave configurada (ex.: CI offline), mas roda
sempre que `OPENROUTER_API_KEY` existe no ambiente.
"""

import json
import os
import unittest
import urllib.request

from models_config import OPENROUTER_MODELS

MODELS_URL = "https://openrouter.ai/api/v1/models"


def _load_live_models():
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    req = urllib.request.Request(MODELS_URL, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return {m["id"] for m in json.loads(resp.read().decode("utf-8"))["data"]}


class TestModelSlugs(unittest.TestCase):
    def test_config_has_no_duplicate_primary_slugs(self):
        primaries = [m.primary_slug for m in OPENROUTER_MODELS]
        self.assertEqual(len(primaries), len(set(primaries)), "slug primário repetido")

    def test_fallbacks_are_not_the_primary(self):
        for mi in OPENROUTER_MODELS:
            self.assertNotIn(mi.primary_slug, mi.fallback_slugs, f"{mi.id}: primário no fallback")

    def test_every_slug_exists_in_live_catalog(self):
        live = _load_live_models()
        if live is None:
            self.skipTest("OPENROUTER_API_KEY ausente: catálogo não consultado")
        dead = []
        for mi in OPENROUTER_MODELS:
            for slug in [mi.primary_slug] + list(mi.fallback_slugs):
                if slug.startswith("~"):
                    # `~vendor/model-latest` é apelido resolvido pelo servidor do
                    # OpenRouter e não aparece no catálogo. Basta existir algum
                    # modelo vivo do mesmo fornecedor (1º segmento do slug).
                    vendor = slug.lstrip("~").split("/")[0]
                    if not any(m.startswith(vendor + "/") for m in live):
                        dead.append((mi.id, slug, "apelido ~ sem modelo vivo do fornecedor"))
                    continue
                if slug not in live:
                    dead.append((mi.id, slug, "slug inexistente"))
        self.assertFalse(dead, "slugs mortos no catálogo do OpenRouter:\n" + "\n".join(
            "  %s -> %s (%s)" % d for d in dead))


if __name__ == "__main__":
    unittest.main()
