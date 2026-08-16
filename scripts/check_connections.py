#!/usr/bin/env python3
"""Vérifie les exports locaux et les connexions n8n / Airtable / Shopify.

Ne jamais afficher les valeurs des secrets.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "exports"
SHOPIFY_API_VERSION = "2026-07"
TIMEOUT_S = 30

# True si au moins un service configuré a échoué.
_failures = 0
_ok = 0


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def env(name: str) -> str:
    return os.environ.get(name, "").strip()


def mask(value: str) -> str:
    if not value:
        return "(vide)"
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}…{value[-4:]} ({len(value)} car.)"


def ok(label: str, detail: str) -> None:
    global _ok
    _ok += 1
    print(f"  OK     {label}: {detail}")


def skip(label: str, detail: str) -> None:
    print(f"  SKIP   {label}: {detail}")


def fail(label: str, detail: str) -> None:
    global _failures
    _failures += 1
    print(f"  ECHEC  {label}: {detail}")


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> tuple[int, object]:
    req = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=context) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, _decode_body(body)
    except urllib.error.URLError as exc:
        raise ConnectionError(str(exc.reason or exc)) from exc
    return status, _decode_body(body)


def _decode_body(body: bytes) -> object:
    text = body.decode("utf-8", errors="replace")
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text[:300]


def list_exports() -> None:
    print("Exports")
    if not EXPORTS.is_dir():
        fail("exports/", "dossier manquant")
        return
    found_any = False
    for sub in ("n8n", "airtable", "shopify", "captures"):
        folder = EXPORTS / sub
        files = []
        if folder.is_dir():
            files = [
                p.name
                for p in sorted(folder.iterdir())
                if p.is_file() and p.name != ".gitkeep"
            ]
        if files:
            found_any = True
            ok(f"exports/{sub}/", ", ".join(files))
        else:
            skip(f"exports/{sub}/", "aucun fichier (ajoute tes exports ici)")
    if found_any:
        return
    skip("exports", "vide pour l’instant — suis docs/parametrage.md")


def normalize_n8n_api_root(base: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/api/v1"):
        return base
    return f"{base}/api/v1"


def check_n8n() -> None:
    print("\nn8n")
    base = env("N8N_BASE_URL")
    key = env("N8N_API_KEY")
    if not base and not key:
        skip("n8n", "N8N_BASE_URL et N8N_API_KEY absents")
        return
    if not base or not key:
        fail("n8n", "il faut N8N_BASE_URL et N8N_API_KEY ensemble")
        return
    print(f"         URL={base}  clé={mask(key)}")
    url = f"{normalize_n8n_api_root(base)}/workflows?limit=50"
    try:
        status, payload = http_json(url, headers={"X-N8N-API-KEY": key, "Accept": "application/json"})
    except ConnectionError as exc:
        fail("n8n", f"réseau : {exc}")
        return
    if status != 200:
        fail("n8n", f"HTTP {status} — clé, URL, ou API indisponible (essai Cloud ?)")
        return
    items = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        fail("n8n", "réponse inattendue")
        return
    names = [str(w.get("name", "?")) for w in items if isinstance(w, dict)][:8]
    extra = "" if len(items) <= 8 else f" (+{len(items) - 8})"
    ok("n8n", f"{len(items)} workflow(s) : {', '.join(names)}{extra}")


def check_airtable() -> None:
    print("\nAirtable")
    pat = env("AIRTABLE_PAT")
    base_id = env("AIRTABLE_BASE_ID")
    if not pat and not base_id:
        skip("Airtable", "AIRTABLE_PAT et AIRTABLE_BASE_ID absents")
        return
    if not pat:
        fail("Airtable", "AIRTABLE_PAT manquant")
        return
    print(f"         PAT={mask(pat)}  base={base_id or '(non fourni)'}")
    headers = {"Authorization": f"Bearer {pat}", "Accept": "application/json"}
    try:
        status, payload = http_json("https://api.airtable.com/v0/meta/bases", headers=headers)
    except ConnectionError as exc:
        fail("Airtable", f"réseau : {exc}")
        return
    if status != 200:
        fail("Airtable", f"HTTP {status} — token ou scopes (data.records:read, schema.bases:read)")
        return
    bases = payload.get("bases", []) if isinstance(payload, dict) else []
    ids = {b.get("id"): b.get("name") for b in bases if isinstance(b, dict)}
    ok("Airtable PAT", f"{len(ids)} base(s) visible(s)")
    if not base_id:
        skip("Airtable base", "ajoute AIRTABLE_BASE_ID (app…)")
        return
    if ids and base_id not in ids:
        fail("Airtable base", f"{base_id} n’est pas dans les ressources du token")
        return
    url = f"https://api.airtable.com/v0/meta/bases/{urllib.parse.quote(base_id)}/tables"
    try:
        status, payload = http_json(url, headers=headers)
    except ConnectionError as exc:
        fail("Airtable tables", f"réseau : {exc}")
        return
    if status != 200:
        fail("Airtable tables", f"HTTP {status}")
        return
    tables = payload.get("tables", []) if isinstance(payload, dict) else []
    names = [t.get("name", "?") for t in tables if isinstance(t, dict)]
    ok("Airtable tables", ", ".join(names) if names else "(aucune)")


def shopify_shop_domain() -> str:
    raw = env("SHOPIFY_STORE_DOMAIN").lower()
    raw = raw.replace("https://", "").replace("http://", "").strip("/")
    if raw.endswith(".myshopify.com"):
        return raw
    if raw:
        return f"{raw}.myshopify.com"
    return ""


def shopify_access_token(shop: str) -> str | None:
    static = env("SHOPIFY_ADMIN_API_TOKEN")
    if static:
        return static
    client_id = env("SHOPIFY_CLIENT_ID")
    client_secret = env("SHOPIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    url = f"https://{shop}/admin/oauth/access_token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode()
    status, payload = http_json(
        url,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=body,
    )
    if status != 200 or not isinstance(payload, dict):
        detail = payload if isinstance(payload, str) else json.dumps(payload)[:400]
        raise RuntimeError(f"échange token HTTP {status}: {detail}")
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("pas d’access_token dans la réponse Shopify")
    return str(token)


def check_shopify() -> None:
    print("\nShopify")
    shop = shopify_shop_domain()
    has_static = bool(env("SHOPIFY_ADMIN_API_TOKEN"))
    has_oauth = bool(env("SHOPIFY_CLIENT_ID") and env("SHOPIFY_CLIENT_SECRET"))
    if not shop and not has_static and not has_oauth:
        skip("Shopify", "aucune variable Shopify")
        return
    if not shop:
        fail("Shopify", "SHOPIFY_STORE_DOMAIN manquant")
        return
    if not has_static and not has_oauth:
        fail("Shopify", "fournis SHOPIFY_CLIENT_ID+SECRET ou SHOPIFY_ADMIN_API_TOKEN")
        return
    print(f"         boutique={shop}  auth={'token Admin' if has_static else 'Dev Dashboard'}")
    try:
        token = shopify_access_token(shop)
    except (ConnectionError, RuntimeError) as exc:
        fail("Shopify token", str(exc))
        return
    url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    query = json.dumps(
        {"query": "{ shop { name myshopifyDomain } }"}
    ).encode()
    try:
        status, payload = http_json(
            url,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": token or "",
            },
            data=query,
        )
    except ConnectionError as exc:
        fail("Shopify API", f"réseau : {exc}")
        return
    if status != 200:
        fail("Shopify API", f"HTTP {status}")
        return
    if not isinstance(payload, dict):
        fail("Shopify API", "réponse inattendue")
        return
    errors = payload.get("errors")
    if errors:
        fail("Shopify API", json.dumps(errors)[:400])
        return
    shop_data = (payload.get("data") or {}).get("shop") or {}
    name = shop_data.get("name") or "?"
    ok("Shopify", f"boutique « {name} » ({shop_data.get('myshopifyDomain', shop)})")


def main() -> int:
    load_dotenv(ROOT / ".env")
    print("Vérification des accès dropshipping\n")
    list_exports()
    check_n8n()
    check_airtable()
    check_shopify()
    print()
    if _failures:
        print(f"Terminé : {_ok} OK, {_failures} échec(s). Voir docs/parametrage.md")
        return 1
    if _ok:
        print(f"Terminé : {_ok} OK. Tu peux demander l’analyse.")
        return 0
    print("Rien à tester encore. Suis docs/parametrage.md (exports ou secrets).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
