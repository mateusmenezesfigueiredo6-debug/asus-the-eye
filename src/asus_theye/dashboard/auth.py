# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Auth mínima do dashboard — fail-closed por desenho.

As apps servidas não tinham autenticação ("local, sem auth externa"). Antes de
expor qualquer coisa na rede, esta camada exige um token Bearer. A postura é
FALHA-FECHADA: se ``require`` está ligado e não há token configurado, a app
**recusa subir** — nunca sobe uma superfície aberta por esquecimento.

O token vem de ``THE_EYE_DASHBOARD_TOKEN``. Comparação em tempo constante
(``hmac.compare_digest``) para não vazar o token por timing. ``/health`` fica
sempre livre (liveness não expõe dado).
"""

from __future__ import annotations

import hmac
import os
from typing import Any

TOKEN_ENV = "THE_EYE_DASHBOARD_TOKEN"
CAMINHOS_LIVRES = ("/health",)


class AuthConfigError(RuntimeError):
    """Configuração de auth impossível de satisfazer com segurança. Recusa subir."""


def _token_configurado() -> str:
    return os.environ.get(TOKEN_ENV, "").strip()


def registrar_auth(app: Any, *, require: bool) -> None:
    """Instala o middleware Bearer. Com ``require=True`` e sem token, LEVANTA.

    ``require`` deve ser ``True`` sempre que a app for exposta fora de localhost.
    """
    token = _token_configurado()
    if require and not token:
        raise AuthConfigError(
            f"exposição exige autenticação, mas {TOKEN_ENV} não está definido. "
            "Defina um token forte antes de servir na rede (falha-fechada)."
        )
    if not token:
        # desenvolvimento local explícito, sem exposição: sem token, sem guarda.
        return

    from starlette.requests import Request
    from starlette.responses import JSONResponse

    @app.middleware("http")
    async def _bearer(request: Request, call_next: Any) -> Any:
        if request.url.path in CAMINHOS_LIVRES:
            return await call_next(request)
        cabecalho = request.headers.get("authorization", "")
        prefixo = "Bearer "
        fornecido = cabecalho[len(prefixo) :] if cabecalho.startswith(prefixo) else ""
        if not fornecido or not hmac.compare_digest(fornecido, token):
            return JSONResponse({"erro": "não autorizado"}, status_code=401)
        return await call_next(request)
