"""
NEMO IDE — Login social (Google / Microsoft / Apple) via OAuth 2.0.

Desenhado para usar apenas a stdlib (urllib). Cada provedor só fica ativo se
as credenciais existirem no ambiente / arquivo .env. Quando nenhum provedor
está configurado, o módulo não interfere no fluxo local (email/senha).

Fluxo (Authorization Code + PKCE):
    1. GET  /api/auth/oauth/{provider}/start   -> redireciona para o provedor
    2. O provedor redireciona para /api/auth/oauth/{provider}/callback
    3. Troca do code por access_token, busca o perfil do usuário
    4. Cria/encontra conta local e emite o token NEMO

Provedores implementados:
    - google    (OpenID Connect - userinfo)
    - microsoft (Entra/Microsoft Graph - userinfo, tenant comum)
    - apple     (Sign in with Apple - JWT id_token, ES256)

Credenciais (em .env):
    GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
    MICROSOFT_CLIENT_ID / MICROSOFT_CLIENT_SECRET
    APPLE_CLIENT_ID / APPLE_TEAM_ID / APPLE_KEY_ID / APPLE_PRIVATE_KEY
        Obs: APPLE_PRIVATE_KEY pode ser o conteúdo (com quebras \n) ou um
        caminho para arquivo .p8. Requer a lib `cryptography` instalada.
    OAUTH_REDIRECT_BASE  -> base publica (ex: https://nemo.onrender.com)
        Se ausente, assume o base do request (schema://host).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

OAUTH_PROVIDERS = ("google", "microsoft", "apple")


class OAuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class ProviderConfig:
    name: str
    enabled: bool
    client_id: str = ""
    client_secret: str = ""
    # específicos Apple
    team_id: str = ""
    key_id: str = ""
    private_key: str = ""


def _env_get(key: str) -> str:
    value = os.getenv(key, "")
    if value:
        return value.strip()
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.is_file():
        try:
            for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line.startswith(key + "="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val
        except Exception:
            return ""
    return ""


def load_configs() -> Dict[str, ProviderConfig]:
    cfgs: Dict[str, ProviderConfig] = {}
    for p in OAUTH_PROVIDERS:
        cfgs[p] = ProviderConfig(name=p, enabled=False)

    cfg = cfgs["google"]
    cfg.client_id = _env_get("GOOGLE_CLIENT_ID")
    cfg.client_secret = _env_get("GOOGLE_CLIENT_SECRET")
    cfg.enabled = bool(cfg.client_id and cfg.client_secret)

    cfg = cfgs["microsoft"]
    cfg.client_id = _env_get("MICROSOFT_CLIENT_ID")
    cfg.client_secret = _env_get("MICROSOFT_CLIENT_SECRET")
    cfg.enabled = bool(cfg.client_id and cfg.client_secret)

    cfg = cfgs["apple"]
    cfg.client_id = _env_get("APPLE_CLIENT_ID")
    cfg.team_id = _env_get("APPLE_TEAM_ID")
    cfg.key_id = _env_get("APPLE_KEY_ID")
    cfg.private_key = _load_apple_key()
    cfg.enabled = bool(
        cfg.client_id and cfg.team_id and cfg.key_id and cfg.private_key
    )
    return cfgs


def _load_apple_key() -> str:
    key = _env_get("APPLE_PRIVATE_KEY")
    if not key:
        return ""
    # Se for caminho de arquivo .p8, carrega o conteúdo
    if "\n" not in key and len(key) < 300 and Path(key).is_file():
        try:
            return Path(key).read_text(encoding="utf-8")
        except Exception:
            return key
    return key.replace("\\n", "\n")


def any_enabled() -> bool:
    return any(c.enabled for c in load_configs().values())


def enabled_providers() -> Dict[str, ProviderConfig]:
    return {name: c for name, c in load_configs().items() if c.enabled}


# ---------------------------------------------------------------------------
# UTIL
# ---------------------------------------------------------------------------

def _random_state(nbytes: int = 24) -> str:
    return base64.urlsafe_b64encode(os.urandom(nbytes)).rstrip(b"=").decode()


def _redirect_base(request) -> str:
    base = _env_get("OAUTH_REDIRECT_BASE")
    if base:
        return base.rstrip("/")
    scheme = request.url.scheme if hasattr(request, "url") else "http"
    host = request.url.netloc if hasattr(request, "url") else f"127.0.0.1:{socket.gethostname() or 8798}"
    return f"{scheme}://{host}"


def _post(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "NEMO-IDE/OAuth",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise OAuthError(f"Provedor OAuth respondeu HTTP {e.code}.", 502)
    except Exception as e:  # noqa: BLE001
        raise OAuthError(f"Falha de rede no provedor OAuth: {e}", 502)
    try:
        return json.loads(raw)
    except Exception:
        raise OAuthError("Resposta inválida do provedor OAuth.", 502)


def _get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "NEMO-IDE/OAuth",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise OAuthError(f"Provedor OAuth respondeu HTTP {e.code}.", 502)
    except Exception as e:  # noqa: BLE001
        raise OAuthError(f"Falha de rede no provedor OAuth: {e}", 502)
    try:
        return json.loads(raw)
    except Exception:
        raise OAuthError("Resposta inválida do provedor OAuth.", 502)


# ---------------------------------------------------------------------------
# PROVEDOR: GOOGLE
# ---------------------------------------------------------------------------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def google_authorize_url(redirect_uri: str, state: str, nonce: str = "") -> str:
    cfg = load_configs()["google"]
    if not cfg.enabled:
        raise OAuthError("Login Google não configurado.", 501)
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    if nonce:
        params["nonce"] = nonce
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def google_exchange(code: str, redirect_uri: str, nonce: str = "") -> Dict[str, Any]:
    cfg = load_configs()["google"]
    data = _post(GOOGLE_TOKEN_URL, {
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })
    access_token = data.get("access_token")
    if not access_token:
        raise OAuthError("Google não retornou access_token.", 502)
    info = _get_json(GOOGLE_USERINFO_URL, {"Authorization": f"Bearer {access_token}"})
    account = {
        "provider": "google",
        "provider_id": info.get("sub") or info.get("id") or "",
        "email": (info.get("email") or "").strip().lower(),
        "name": info.get("name") or info.get("given_name") or "Novo usuário",
        "picture": info.get("picture") or "",
        "email_verified": info.get("email_verified") is True or str(info.get("email_verified", "")).lower() == "true",
    }
    if not account["email"] or not account["provider_id"]:
        raise OAuthError("Google não retornou perfil válido.", 502)
    if not account["email_verified"]:
        raise OAuthError("Google não confirmou o e-mail da conta.", 403)
    return account


# ---------------------------------------------------------------------------
# PROVEDOR: MICROSOFT
# ---------------------------------------------------------------------------

MS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"


def microsoft_authorize_url(redirect_uri: str, state: str, nonce: str = "") -> str:
    cfg = load_configs()["microsoft"]
    if not cfg.enabled:
        raise OAuthError("Login Microsoft não configurado.", 501)
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile User.Read offline_access",
        "state": state,
        "response_mode": "query",
    }
    if nonce:
        params["nonce"] = nonce
    return MS_AUTH_URL + "?" + urllib.parse.urlencode(params)


def microsoft_exchange(code: str, redirect_uri: str, nonce: str = "") -> Dict[str, Any]:
    cfg = load_configs()["microsoft"]
    data = _post(MS_TOKEN_URL, {
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "scope": "User.Read",
    })
    access_token = data.get("access_token")
    if not access_token:
        raise OAuthError("Microsoft não retornou access_token.", 502)
    info = _get_json(MS_USERINFO_URL, {"Authorization": f"Bearer {access_token}"})
    account = {
        "provider": "microsoft",
        "provider_id": info.get("id") or info.get("sub") or "",
        "email": (info.get("mail") or info.get("userPrincipalName") or "")
            .strip().lower(),
        "name": info.get("displayName") or "Novo usuário",
        "picture": "",
        "email_verified": True,
    }
    try:
        account["email"] = account["email"].replace("#EXT#", "").lower()
    except Exception:
        pass
    if not account["email"] or not account["provider_id"]:
        raise OAuthError("Microsoft não retornou perfil válido.", 502)
    return account


# ---------------------------------------------------------------------------
# PROVEDOR: APPLE
# ---------------------------------------------------------------------------

APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"


def _apple_client_secret() -> str:
    """Gera o client_secret (JWT ES256) para Sign in with Apple."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except Exception as e:  # noqa: BLE001
        raise OAuthError(
            "Biblioteca 'cryptography' necessária para o login Apple. "
            f"Execute: pip install cryptography ({e})", 501)

    cfg = load_configs()["apple"]
    now = int(os.environ.get("APPLE_IAT_TRICK", "0"))
    iat = now if now else int(time.time())
    exp = iat + 6 * 60 * 60  # 6 horas (máximo permitido)

    header = {"alg": "ES256", "kid": cfg.key_id}
    payload = {
        "iss": cfg.team_id,
        "iat": iat,
        "exp": exp,
        "aud": "https://appleid.apple.com",
        "sub": cfg.client_id,
    }

    def _b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _b64obj(obj: Dict[str, Any]) -> str:
        return _b64(json.dumps(obj, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{_b64obj(header)}.{_b64obj(payload)}".encode("utf-8")
    private_key = serialization.load_pem_private_key(
        cfg.private_key.encode("utf-8"), password=None)
    signature = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    # ASN.1 DER -> raw r||s (formato esperado pelo Apple)
    r_len = signature[3]
    r = int.from_bytes(signature[4:4 + r_len], "big")
    s = int.from_bytes(signature[4 + r_len + 2:], "big")
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{signing_input.decode()}.{_b64(raw)}"


def apple_authorize_url(redirect_uri: str, state: str, nonce: str = "") -> str:
    cfg = load_configs()["apple"]
    if not cfg.enabled:
        raise OAuthError("Login Apple não configurado.", 501)
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "name email",
        "response_mode": "form_post",
        "state": state,
    }
    if nonce:
        params["nonce"] = nonce
    return APPLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _verify_apple_id_token(id_token: str, client_id: str) -> Dict[str, Any]:
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
    except Exception as exc:
        raise OAuthError(f"Biblioteca 'cryptography' necessária para validar o Apple: {exc}", 501)

    parts = id_token.split(".")
    if len(parts) != 3:
        raise OAuthError("Apple id_token malformado.", 502)
    try:
        header = json.loads(_decode_base64url(parts[0]))
        claims = json.loads(_decode_base64url(parts[1]))
        signature = _decode_base64url(parts[2])
    except Exception:
        raise OAuthError("Apple id_token não pôde ser decodificado.", 502)
    if header.get("alg") != "ES256":
        raise OAuthError("Algoritmo de assinatura Apple inválido.", 502)
    keys = _get_json(APPLE_JWKS_URL).get("keys", [])
    key_data = next((key for key in keys if key.get("kid") == header.get("kid")), None)
    if not key_data:
        raise OAuthError("Chave de assinatura Apple não encontrada.", 502)
    try:
        x = int.from_bytes(_decode_base64url(str(key_data["x"])), "big")
        y = int.from_bytes(_decode_base64url(str(key_data["y"])), "big")
        public_key = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
        public_key.verify(
            signature,
            f"{parts[0]}.{parts[1]}".encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
    except Exception:
        raise OAuthError("Assinura do id_token Apple inválida.", 502)

    now = int(time.time())
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if claims.get("iss") != "https://appleid.apple.com" or client_id not in audiences:
        raise OAuthError("Claims do Apple inválidos.", 502)
    try:
        if int(claims.get("exp", 0)) <= now:
            raise OAuthError("id_token Apple expirado.", 502)
    except (TypeError, ValueError):
        raise OAuthError("Expiração do id_token Apple inválida.", 502)
    return claims


def apple_exchange(code: str, redirect_uri: str, expected_nonce: str = "") -> Dict[str, Any]:
    cfg = load_configs()["apple"]
    data = _post(APPLE_TOKEN_URL, {
        "client_id": cfg.client_id,
        "client_secret": _apple_client_secret(),
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })
    id_token = data.get("id_token")
    if not id_token:
        raise OAuthError("Apple não retornou id_token.", 502)
    claims = _verify_apple_id_token(id_token, cfg.client_id)
    if expected_nonce and claims.get("nonce") != expected_nonce:
        raise OAuthError("Nonce do Apple não confere.", 403)
    account = {
        "provider": "apple",
        "provider_id": claims.get("sub") or "",
        "email": (claims.get("email") or "").strip().lower(),
        "name": claims.get("name") or "Novo usuário",
        "picture": "",
        "email_verified": claims.get("email_verified") is True or str(claims.get("email_verified", "")).lower() == "true",
    }
    if not account["provider_id"]:
        raise OAuthError("Apple não retornou sub no id_token.", 502)
    if not account["email"]:
        account["email"] = account["provider_id"] + "@privaterelay.appleid.com"
        account["name"] = "Usuário Apple"
        account["email_verified"] = True
    if not account["email_verified"]:
        raise OAuthError("Apple não confirmou o e-mail da conta.", 403)
    return account


# ---------------------------------------------------------------------------
# DESPACHO
# ---------------------------------------------------------------------------

def authorize_url(provider: str, redirect_uri: str, state: str, nonce: str = "") -> str:
    fn = {
        "google": google_authorize_url,
        "microsoft": microsoft_authorize_url,
        "apple": apple_authorize_url,
    }.get(provider)
    if not fn:
        raise OAuthError(f"Provedor OAuth desconhecido: {provider}", 400)
    return fn(redirect_uri, state, nonce)


def exchange(provider: str, code: str, redirect_uri: str, nonce: str = "") -> Dict[str, Any]:
    fn = {
        "google": google_exchange,
        "microsoft": microsoft_exchange,
        "apple": apple_exchange,
    }.get(provider)
    if not fn:
        raise OAuthError(f"Provedor OAuth desconhecido: {provider}", 400)
    return fn(code, redirect_uri, nonce)
