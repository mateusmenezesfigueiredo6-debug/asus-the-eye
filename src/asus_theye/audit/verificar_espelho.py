"""N2 — verifica se o espelho da corrente local está em dia no D1.

Compara ``reports/markets/eventos.jsonl`` (corrente local) com o endpoint
``GET /events?tenant=`` do worker restrito. A corrente quebrada não se compara:
``verify_chain`` roda **antes** de qualquer requisição de rede.

O GET do worker devolve no máximo 50 eventos. Se a corrente local tiver mais de
50 eventos selados, a janela é parcial e o relatório diz isso explicitamente em
vez de fingir cobertura total.

Retorno (todos os casos bem-sucedidos)::

    {
        "locais": N,
        "espelhos_remotos": M,
        "faltantes_na_janela": [...],
        "janela_parcial": bool,
        "verifica_local": true,
    }
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from asus_theye.audit.remote_ledger import _ledger_token  # noqa: PLC2701
from asus_theye.audit.schema import verify_chain
from asus_theye.audit.sync_ledger import EVENTOS_PADRAO, RECURSO_ESPELHO

_TIMEOUT = 30
_JANELA_REMOTA = 50  # o worker devolve os últimos N — mantém a semântica honesta


class CorrenteBrokenError(RuntimeError):
    """Levantada quando verify_chain falha antes de qualquer comparação."""


class VerificarEspelhoError(RuntimeError):
    """Erros de rede ou resposta inesperada do worker."""


def _buscar_padrao(ledger_url: str, tenant: str) -> dict[str, Any]:
    """GET <ledger_url>/events?tenant=<tenant> com bearer quando disponível."""
    url = f"{ledger_url.rstrip('/')}/events?tenant={tenant}"
    headers: dict[str, str] = {
        "user-agent": "asus-theye-audit-client/0.2",
    }
    token = _ledger_token()
    if token:
        headers["authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            corpo: dict = json.loads(resp.read().decode("utf-8"))
            return corpo
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise VerificarEspelhoError(f"worker recusou: HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise VerificarEspelhoError(f"worker inacessível: {exc}") from exc


def verificar(
    ledger_url: str,
    *,
    eventos: Path = EVENTOS_PADRAO,
    tenant: str = "tenant-demo",
    buscar: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compara a corrente local com o espelho no D1.

    Parâmetros
    ----------
    ledger_url:
        URL base do worker (ex: ``https://ledger.example.com``).
    eventos:
        Caminho para o ``eventos.jsonl`` local.
    tenant:
        Identificador do tenant no worker.
    buscar:
        Função injetável ``(url, tenant) -> dict``. Padrão: GET real com
        ``urllib`` (ver :func:`_buscar_padrao`). Use em testes para rodar
        offline.

    Levanta
    -------
    FileNotFoundError
        Se ``eventos`` não existe.
    CorrenteBrokenError
        Se ``verify_chain`` detecta corrente inválida.
    VerificarEspelhoError
        Em falha de rede ou resposta inesperada.
    """
    if not eventos.exists():
        raise FileNotFoundError(f"corrente não encontrada: {eventos}")

    linhas = [ln for ln in eventos.read_text(encoding="utf-8").splitlines() if ln.strip()]
    corrente_local = [json.loads(ln) for ln in linhas]

    if not verify_chain(corrente_local):
        raise CorrenteBrokenError("verify_chain falhou — corrente inválida, comparação abortada")

    # hashes locais das sequências "sealed_event_mirror"-elegíveis
    hashes_locais: list[str] = [ev["event_hash_sha256"] for ev in corrente_local]
    n_locais = len(hashes_locais)

    _buscar = buscar if buscar is not None else _buscar_padrao
    resposta = _buscar(ledger_url, tenant)

    eventos_remotos: list[dict[str, Any]] = resposta.get("events", [])
    espelhos_remotos = [ev for ev in eventos_remotos if ev.get("resource_type") == RECURSO_ESPELHO]
    n_espelhos = len(espelhos_remotos)

    # hashes dos espelhos visíveis na janela
    hashes_espelhados: set[str] = set()
    for esp in espelhos_remotos:
        # o idempotency_key codifica o hash: "espelho-<hash[:32]>"
        chave: str = esp.get("idempotency_key", "")
        prefixo = "espelho-"
        if chave.startswith(prefixo):
            hashes_espelhados.add(chave[len(prefixo) :])

    janela_parcial = n_locais > _JANELA_REMOTA

    # O GET atual do worker NÃO devolve idempotency_key (verificado em produção
    # 20/08/2026): o matching por hash só é possível quando o campo existir na
    # resposta. Sem ele, afirmar "faltante" seria falso positivo estrutural —
    # o que dá para PROVAR é a cobertura por contagem da janela visível.
    matching_por_hash = bool(hashes_espelhados)
    faltantes: list[str] = []
    if matching_por_hash:
        faltantes = [h for h in hashes_locais if h[:32] not in hashes_espelhados]
        if janela_parcial:
            # fora da janela o hash não aparece mesmo estando espelhado
            faltantes = faltantes[-_JANELA_REMOTA:] if len(faltantes) > _JANELA_REMOTA else faltantes
    cobertura_da_janela = n_espelhos >= min(n_locais, _JANELA_REMOTA)

    return {
        "locais": n_locais,
        "espelhos_remotos": n_espelhos,
        "faltantes_na_janela": faltantes,
        "matching_por_hash": matching_por_hash,
        "cobertura_da_janela": cobertura_da_janela,
        "janela_parcial": janela_parcial,
        "verifica_local": True,
    }
