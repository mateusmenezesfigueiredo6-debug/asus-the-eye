# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Liga a varredura da missao ao grafo de fontes — a etapa 1 deixa de ser 0,0%.

A varredura ja media volume por campo, mas o numero morria num relatorio. O
grafo so conta uma fonte quando ela cumpre o `knowledge-source.schema.json`
inteiro: identidade, jurisdicao, licenca, manifesto, classe de alegacao e
revisao humana. Este modulo faz essa travessia.

O QUE VIRA FONTE QUALIFICADA

  ROR   cada instituicao devolvida vira uma entrada `institution`: tem
        identificador estavel, nome oficial, pais e URL propria.
  DOAJ  cada periodico vira `journal`: estar no DOAJ ja e verificacao de
        acesso aberto declarado.

Crossref e arXiv NAO viram fonte: eles devolvem TRABALHOS, nao entidades. Um
artigo nao e uma fonte de conhecimento no sentido do grafo — a fonte seria o
periodico ou o grupo que o produziu, e derivar isso do metadado exigiria passo
que ainda nao existe. Registrar artigo como fonte inflaria a cobertura sem
acrescentar entidade, que e exatamente o tipo de numero que este projeto recusa.

REVISAO HUMANA PENDENTE POR CONSTRUCAO
Toda fonte entra com `human_review.status = "pending"`. O schema exige
`required: true` e nao ha automatismo que aprove: quem aprova e pessoa. A
cobertura sobe porque a fonte existe e esta identificada, nao porque alguem
disse que ela presta.

Uso: python3 apps/observatorio/alimentar_grafo.py [--aplicar]
Saida: data/source-graph/sources.json (so com --aplicar)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "src"))

from asus_theye.source_graph.connectors.academico import doaj, ror  # noqa: E402
from asus_theye.source_graph.coverage import build_coverage  # noqa: E402

DESTINO = BASE / "data/source-graph/sources.json"
CAMPOS = [
    "artificial intelligence",
    "machine learning",
    "quantum computing",
    "robotics",
    "causal inference",
    "time series",
    "forecasting",
    "quantum machine learning",
]


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _base(
    source_id: str,
    categoria: str,
    tipo: str,
    nome: str,
    url: str,
    jurisdicao: str,
    tier: int,
    consulta: str,
    prov: dict,
) -> dict:
    """Os 14 campos que o schema exige, preenchidos com o que se mediu."""
    return {
        "source_id": source_id,
        "category_id": categoria,
        "entity_type": tipo,
        "official_name": nome,
        "official_url": url,
        "jurisdiction": jurisdicao,
        "authority_tier": tier,
        "source_manifest": [
            {
                "url": prov["url"],
                "sha256": prov["sha256_resposta"],
                "retrieved_at": prov["coletado_em_utc"],
                "connector": prov["conector"],
            }
        ],
        "discovery_query_id": f"missao::{consulta}",
        "first_seen_at": _agora(),
        "last_verification_at": _agora(),
        "claim_class": "FACT",
        "license": {
            "license_id": "CC0-1.0" if prov["conector"] == "ror" else "declarada-pela-fonte",
            "license_url": ("https://ror.org/about/" if prov["conector"] == "ror" else "https://doaj.org/docs/faq/"),
        },
        "human_review": {"required": True, "status": "pending"},
        "poc_status": "production",
    }


def coletar_fontes() -> tuple[list[dict], list[str]]:
    fontes, vistos, notas = [], set(), []
    for campo in CAMPOS:
        try:
            r = ror(campo, limite=10)
        except Exception as e:  # noqa: BLE001
            notas.append(f"ror/{campo}: {type(e).__name__}")
            r = None
        if r:
            for it in r["itens"]:
                sid = it["ror_id"]
                if not sid or sid in vistos or not it.get("nome"):
                    continue
                vistos.add(sid)
                fontes.append(
                    _base(
                        sid,
                        "research-centers",
                        "institution",
                        it["nome"],
                        sid,
                        it.get("pais") or "unknown",
                        2,
                        campo,
                        r["proveniencia"],
                    )
                )

        try:
            d = doaj(campo, limite=10)
        except Exception as e:  # noqa: BLE001
            notas.append(f"doaj/{campo}: {type(e).__name__}")
            continue
        for it in d["itens"]:
            issn = it.get("issn")
            sid = f"doaj:{issn}" if issn else None
            if not sid or sid in vistos or not it.get("titulo"):
                continue
            vistos.add(sid)
            fontes.append(
                _base(
                    sid,
                    "academics-and-researchers",
                    "journal",
                    it["titulo"],
                    f"https://doaj.org/toc/{issn}",
                    it.get("pais") or "unknown",
                    2,
                    campo,
                    d["proveniencia"],
                )
            )
    return fontes, notas


def main(aplicar: bool = False) -> None:
    antes = build_coverage([])
    fontes, notas = coletar_fontes()
    depois = build_coverage(fontes)

    def cobertas(rel):
        return [c for c in rel["by_category"] if c["qualified_count"] > 0]

    print(f"fontes qualificadas montadas: {len(fontes)}")
    if notas:
        print(f"  falhas registradas: {notas}")
    print(f"  categorias com cobertura: antes {len(cobertas(antes))}, depois {len(cobertas(depois))}")
    for c in cobertas(depois):
        print(
            f"    {c['category_id']:<28} {c['qualified_count']:>4} fontes  "
            f"{c['coverage_pct']:>6.2f}%  motivo={c['blocking_reason']}"
        )

    por_tipo: dict[str, int] = {}
    for f in fontes:
        por_tipo[f["entity_type"]] = por_tipo.get(f["entity_type"], 0) + 1
    print(f"  por tipo: {por_tipo}")
    print("  revisao humana: todas pendentes (o schema exige pessoa, nao automatismo)")

    if aplicar:
        DESTINO.write_text(
            json.dumps(
                {
                    "generated_at": _agora(),
                    "note": (
                        "fontes descobertas pela varredura da missao; toda entrada "
                        "tem manifesto com SHA-256 da resposta e revisao humana "
                        "pendente"
                    ),
                    "discovery_fields": CAMPOS,
                    "sources": fontes,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nOK {DESTINO.relative_to(BASE)} — {len(fontes)} fontes gravadas")
    else:
        print("\n(simulacao — use --aplicar para gravar em data/source-graph/sources.json)")


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
