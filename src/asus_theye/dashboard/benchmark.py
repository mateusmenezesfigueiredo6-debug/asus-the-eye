"""Dependency-light dashboard page for the latest benchmark evidence."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"results": {}, "metrics": {}, "conclusion": "Run `asus-theye benchmark` first."}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries[-20:]


def _svg_bar_chart(
    points: list[tuple[str, float]],
    *,
    aria_label: str,
    formatter: str = "{value:.3f}",
    empty_message: str = "No data available.",
) -> str:
    if not points:
        safe_message = html.escape(empty_message)
        return (
            '<svg class="chart-svg" viewBox="0 0 582 72" role="img" '
            f'aria-label="{html.escape(aria_label)}">'
            '<rect x="12" y="12" width="558" height="48" rx="8" fill="#213047"></rect>'
            f'<text x="28" y="42" fill="#9aa8bd">{safe_message}</text>'
            "</svg>"
        )

    chart_width = 320
    label_x = 12
    bar_x = 172
    value_x = bar_x + chart_width + 10
    row_height = 30
    svg_width = value_x + 80
    svg_height = 16 + (len(points) * row_height)
    max_value = max((value for _, value in points), default=0.0)

    parts = [
        (
            f'<svg class="chart-svg" viewBox="0 0 {svg_width} {svg_height}" '
            f'role="img" aria-label="{html.escape(aria_label)}">'
        )
    ]
    for index, (name, value) in enumerate(points):
        y = 22 + (index * row_height)
        width = 0.0 if max_value <= 0 else max(0.0, chart_width * value / max_value)
        safe_name = html.escape(name)
        safe_value = html.escape(formatter.format(value=value))
        parts.extend(
            (
                f'<text x="{label_x}" y="{y}" fill="currentColor">{safe_name}</text>',
                (f'<rect x="{bar_x}" y="{y - 13}" width="{chart_width}" height="16" rx="4" fill="#213047"></rect>'),
                (f'<rect x="{bar_x}" y="{y - 13}" width="{width:.2f}" height="16" rx="4" fill="#67e8f9"></rect>'),
                f'<text x="{value_x}" y="{y}" fill="#9aa8bd">{safe_value}</text>',
            )
        )
    parts.append("</svg>")
    return "".join(parts)


def benchmark_page(report_path: str | Path = "reports/benchmark/latest.json") -> str:
    resolved_report_path = Path(report_path)
    report = _load(resolved_report_path)
    history = _load_history(resolved_report_path.with_name("history.jsonl"))
    results = report.get("results", {})
    metrics = report.get("metrics", {})
    scores = {name: float(value.get("score", 0)) for name, value in results.items()}
    times = {name: float(value.get("execution_time_ms", 0)) for name, value in results.items()}
    best_score_solver = max(scores, key=lambda name: scores[name]) if scores else None
    best_time_solver = min(times, key=lambda name: times[name]) if times else None
    best_score = f"{scores[best_score_solver]:.3f} ({best_score_solver})" if best_score_solver else "n/a"
    best_time = f"{times[best_time_solver]:.3f} ms ({best_time_solver})" if best_time_solver else "n/a"
    qar = metrics.get("qar", {}).get("qar", "n/a")
    stability = metrics.get("stability", {}).get("standard_deviation", "n/a")
    history_points = [
        {
            "date": entry["date"],
            "best_score": max(entry.get("scores", {}).values(), default=0),
        }
        for entry in history
    ]
    score_chart = _svg_bar_chart(
        list(scores.items()),
        aria_label="Score comparison",
        formatter="{value:.3f}",
        empty_message="No benchmark scores yet.",
    )
    time_chart = _svg_bar_chart(
        list(times.items()),
        aria_label="Execution time",
        formatter="{value:.3f} ms",
        empty_message="No benchmark timings yet.",
    )
    history_chart = _svg_bar_chart(
        [(point["date"], float(point["best_score"])) for point in history_points],
        aria_label="History",
        formatter="{value:.3f}",
        empty_message="No benchmark history yet.",
    )
    conclusion = html.escape(str(report.get("conclusion", "")))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE Benchmark</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em}}
.cards,.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}}
.card,.chart{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
.chart-svg{{width:100%;height:auto;display:block}}
.label{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.muted{{color:var(--muted)}}
.value{{font-size:1.7rem;margin-top:8px;color:var(--accent)}}
</style></head><body><main><h1>ASUS THE EYE BENCHMARK</h1>
<section class="cards"><div class="card">
<div class="label">Best score</div><div class="value">{best_score}</div></div>
<div class="card"><div class="label">Best time</div><div class="value">{best_time}</div></div>
<div class="card"><div class="label">QAR</div><div class="value">{qar}</div></div>
<div class="card"><div class="label">Stability σ</div>
<div class="value">{stability}</div></div></section>
<section class="charts"><div class="chart"><h2>Score comparison</h2>{score_chart}</div>
<div class="chart"><h2>Execution time</h2>{time_chart}</div>
<div class="chart"><h2>History</h2>
{history_chart}</div></section>
<p>{conclusion}</p>
</main></body></html>"""


def register_benchmark_routes(app: Any, report_path: str | Path = "reports/benchmark/latest.json") -> None:
    """Attach GET /benchmark to a FastAPI-compatible application."""

    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/benchmark", response_class=HTMLResponse)
    def get_benchmark() -> str:
        return benchmark_page(report_path)
