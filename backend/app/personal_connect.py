"""Read-only OAuth authorization-code connect flow for eBay/StockX-style providers.

`SPECS` is deliberately empty: authorize/token URLs and scopes must come from each provider's
official docs, which have not been read yet (see docs/personal-feeds-providers.md). Everything
else here (signed state, code exchange, encrypted storage) is provider-independent and tested.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlencode

import httpx

from . import personal_vault

logger = logging.getLogger("aisaac.personal")

STATE_MAX_AGE = 600  # seconds the consent link stays valid


@dataclass(frozen=True)
class ProviderSpec:
    authorize_url: str
    token_url: str
    scopes: tuple[str, ...]
    client_id: str
    client_secret: str
    redirect: str = ""  # fixed redirect_uri (eBay wants its RuName); empty = our callback URL
    extra_authorize: tuple[tuple[str, str], ...] = ()
    secret_in_body: bool = False  # StockX sends client creds in the form body, eBay via Basic auth


SPECS: dict[str, ProviderSpec] = {}


def make_specs(
    ebay_id: str, ebay_secret: str, ebay_runame: str, ebay_scopes: str,
    stockx_id: str, stockx_secret: str,
) -> dict[str, ProviderSpec]:
    """Provider specs from the official OAuth docs; a provider with missing settings is omitted.

    eBay scopes are copied from the dev portal's Application Keys page (space-separated).
    """
    specs: dict[str, ProviderSpec] = {}
    if ebay_id and ebay_secret and ebay_runame and ebay_scopes.strip():
        specs["ebay"] = ProviderSpec(
            "https://auth.ebay.com/oauth2/authorize",
            "https://api.ebay.com/identity/v1/oauth2/token",
            tuple(ebay_scopes.split()), ebay_id, ebay_secret, redirect=ebay_runame,
        )
    if stockx_id and stockx_secret:
        specs["stockx"] = ProviderSpec(
            "https://accounts.stockx.com/authorize",
            "https://accounts.stockx.com/oauth/token",
            ("offline_access", "openid"), stockx_id, stockx_secret,
            extra_authorize=(("audience", "gateway.stockx.com"),), secret_in_body=True,
        )
    return specs

Exchange = Callable[[ProviderSpec, str, str], str]  # (spec, code, redirect_uri) -> refresh token


class ConnectError(Exception):
    pass


def _sign(secret: str, body: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def make_state(provider: str, secret: str, now: Optional[float] = None) -> str:
    body = f"{provider}.{int(now if now is not None else time.time())}.{secrets.token_hex(8)}"
    return f"{body}.{_sign(secret, body)}"


def check_state(state: str, provider: str, secret: str, now: Optional[float] = None) -> bool:
    body, _, sig = state.rpartition(".")
    parts = body.split(".")
    ts = parts[1] if len(parts) == 3 else ""
    if not secret or len(parts) != 3 or parts[0] != provider or not (ts.isascii() and ts.isdigit()):
        return False
    age = (now if now is not None else time.time()) - int(parts[1])
    good = hmac.compare_digest(sig.encode(), _sign(secret, body).encode())
    return good and 0 <= age <= STATE_MAX_AGE


def redirect_uri(base_url: str, provider: str) -> str:
    return f"{base_url.rstrip('/')}/api/v1/personal/connect/{provider}/callback"


def authorize_link(provider: str, key: str, base_url: str, now: Optional[float] = None) -> str:
    spec = SPECS.get(provider)
    if spec is None or not key or not spec.client_id:
        raise ConnectError("not configured")
    query = urlencode({
        "response_type": "code",
        "client_id": spec.client_id,
        "redirect_uri": spec.redirect or redirect_uri(base_url, provider),
        "scope": " ".join(spec.scopes),
        "state": make_state(provider, key, now),
        **dict(spec.extra_authorize),
    })
    return f"{spec.authorize_url}?{query}"


def _http_exchange(spec: ProviderSpec, code: str, redirect: str) -> str:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": spec.redirect or redirect,
    }
    if spec.secret_in_body:
        data |= {"client_id": spec.client_id, "client_secret": spec.client_secret}
    response = httpx.post(
        spec.token_url,
        data=data,
        auth=None if spec.secret_in_body else (spec.client_id, spec.client_secret),
        timeout=10,
    )
    response.raise_for_status()
    return str(response.json()["refresh_token"])


def complete(
    provider: str, code: str, state: str, key: str, base_url: str,
    exchange: Exchange = _http_exchange, now: Optional[float] = None,
) -> None:
    """Verify state, swap the code for a refresh token and store it encrypted."""
    spec = SPECS.get(provider)
    if spec is None or not check_state(state, provider, key, now):
        raise ConnectError("invalid state")
    try:
        token = exchange(spec, code, redirect_uri(base_url, provider))
        personal_vault.save_token(provider, token, key)
    except Exception as exc:  # never surface provider or crypto detail; log only the class
        logger.warning("oauth exchange failed: %s", type(exc).__name__)
        raise ConnectError("exchange failed") from None
