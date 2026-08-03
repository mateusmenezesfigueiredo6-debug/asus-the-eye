"""Os três relatórios que a Phase C exige e que faltavam no disco."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"

REASON_LABELS = {
    "none": "coberto",
    "not_yet_attempted": "ainda não tentado",
    "requires_dpia": "exige DPIA humana",
    "requires_paid_api": "exige fonte paga",
    "license_restricted": "licença restringe",
    "robots_disallowed": "robots proíbe",
    "no_free_source": "não existe fonte gratuita",
}


def _header(title: str, coverage: dict[str, Any]) -> list[str]:
    return [
        f"# {title}",
        "",
        f"Gerado em {datetime.now(timezone.utc).date().isoformat()} · "
        f"metodologia {coverage['methodology_version']} · "
        f"snapshot `{coverage['snapshot_hash_sha256'][:16]}…`",
        "",
    ]


def coverage_report(coverage: dict[str, Any], tracks: dict[str, Any]) -> str:
    lines = _header("Cobertura do grafo de fontes", coverage)
    lines += [
        "Números reais. Nenhuma lista é preenchida até o alvo, e todo zero tem um",
        "motivo nomeado — a diferença entre *não temos* e *não olhamos*.",
        "",
        "## Por trilha",
        "",
        "| Trilha | Qualificadas | Alvo | Cobertura | Motivos |",
        "| --- | --- | --- | --- | --- |",
    ]
    for track, data in tracks.items():
        reasons = " · ".join(
            f"{REASON_LABELS.get(k, k)} ×{v}" for k, v in sorted(data["blocking_reasons"].items())
        )
        lines.append(
            f"| {track} | {data['qualified']} | {data['target']} | "
            f"{data['coverage_pct']}% | {reasons} |"
        )

    lines += ["", "## Por categoria", "", "| Categoria | Qualificadas | Alvo | Motivo |", "| --- | --- | --- | --- |"]
    for entry in coverage["by_category"]:
        lines.append(
            f"| {entry['category_id']} | {entry['qualified_count']} | {entry['target_size']} | "
            f"{REASON_LABELS.get(entry['blocking_reason'], entry['blocking_reason'])} |"
        )

    covered_niches = sum(1 for n in coverage["by_niche"] if n["qualified_count"] > 0)
    lines += [
        "",
        "## Por nicho",
        "",
        f"{covered_niches} de {len(coverage['by_niche'])} nichos têm ao menos uma fonte "
        "qualificada.",
        "",
    ]
    return "\n".join(lines)


def gaps_report(coverage: dict[str, Any]) -> str:
    lines = _header("Lacunas de fonte", coverage)
    lines += [
        "Cada lacuna com o motivo e o que a destravaria. Uma lacuna sem saída",
        "declarada é uma lacuna escondida.",
        "",
        "| Motivo | Lacuna | O que destravaria |",
        "| --- | --- | --- |",
    ]
    for gap in coverage["gaps"]:
        reason = REASON_LABELS.get(gap["blocking_reason"], gap["blocking_reason"])
        lines.append(
            f"| {reason} | {gap['description']} | {gap.get('what_would_unblock', '—')} |"
        )
    lines.append("")
    return "\n".join(lines)


def limitations_report(coverage: dict[str, Any]) -> str:
    lines = _header("Limitações do ranking", coverage)
    lines += [
        "O que os números desta plataforma **não** significam.",
        "",
        "## Estruturais",
        "",
        "- **Componente ausente é omitido, nunca zerado.** Um score de 3-de-7",
        "  componentes não é comparável a um de 7-de-7; `components_present` e",
        "  `components_declared` viajam junto de todo score exatamente por isso.",
        "- **Listas não são preenchidas.** `qualified_count` é o real e `padded` é",
        "  sempre `false` — o schema não tem como representar o contrário.",
        "- **Pessoas não são ranqueadas.** É L4 e exige DPIA humana; o pipeline",
        "  levanta se alguém tentar.",
        "- **Nenhuma métrica social entra no score.** `component_id` é enum",
        "  fechado: `follower_count` levanta em vez de ser ignorado.",
        "",
        "## De cobertura",
        "",
        f"- Nenhuma busca foi executada ainda: todos os {len(coverage['by_category'])}",
        "  contadores de categoria estão em zero por `not_yet_attempted`, não por",
        "  ausência de entidades no mundo.",
        "- As licenças dos artefatos de software são as **declaradas** pelos",
        "  projetos, não verificadas com hash — todos em `declared_unverified`.",
        "",
        "## De fonte",
        "",
        "- Volume de vendas de livros e tamanho de mercado por nicho exigem fonte",
        "  licenciada. Derivar de nota, resenha ou interesse de busca seria proxy",
        "  vendido como medição.",
        "- Algoritmos proprietários de recomendação não são públicos. O que se",
        "  indexa são as publicações das empresas e as divulgações obrigatórias.",
        "- Contagem de citações do Crossref é parcial; do OpenAlex, hoje paga.",
        "",
    ]
    return "\n".join(lines)


def write_reports(coverage: dict[str, Any], tracks: dict[str, Any]) -> list[Path]:
    """Escreve os três relatórios da Phase C. Devolve os caminhos."""
    targets = {
        "LEGAL_SOURCE_COVERAGE.md": coverage_report(coverage, tracks),
        "SOURCE_GAPS.md": gaps_report(coverage),
        "RANKING_LIMITATIONS.md": limitations_report(coverage),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in targets.items():
        path = REPORTS_DIR / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
