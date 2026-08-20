# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
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
    payload = json.dumps({"scores": scores, "times": times, "history": history_points}).replace("<", "\\u003c")
    conclusion = html.escape(str(report.get("conclusion", "")))
    corpo = f"""<section class="cards"><div class="card">
<div class="label">Best score</div><div class="value">{best_score}</div></div>
<div class="card"><div class="label">Best time</div><div class="value">{best_time}</div></div>
<div class="card"><div class="label">QAR</div><div class="value">{qar}</div></div>
<div class="card"><div class="label">Stability σ</div>
<div class="value">{stability}</div></div></section>
<div class="table-wrap"><section class="charts">
<div class="chart"><h2>Score comparison</h2><div id="scores"></div></div>
<div class="chart"><h2>Execution time</h2><div id="times"></div></div>
<div class="chart"><h2>History</h2>
<div id="history"></div></div></section></div>
<p>{conclusion}</p>"""
    return _shell(corpo, payload)


def _shell(corpo: str, payload: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ASUS THE EYE Benchmark</title><style>
:root{{--ink:#e9f0ff;--muted:#9aa8bd;--panel:#151d2b;--accent:#67e8f9;--bg:#080d16}}
*{{box-sizing:border-box}}
body{{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font:16px system-ui}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
h1{{letter-spacing:.08em}}
.cards,.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}}
.card,.chart{{background:var(--panel);padding:20px;border:1px solid #253149;border-radius:12px}}
.label{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.value{{font-size:1.7rem;margin-top:8px;color:var(--accent)}}
.table-wrap{{width:100%;max-width:100%;overflow-x:auto}}
.bar{{height:24px;background:#213047;margin:8px 0;border-radius:5px;overflow:hidden}}
.bar i{{display:block;height:100%;background:var(--accent)}}
.chart{{min-width:0}}
@media (max-width: 640px){{
main{{padding:24px 12px}}
.cards,.charts{{grid-template-columns:1fr}}
.label{{font-size:.72rem}}
h2{{font-size:1rem}}
}}
</style></head><body><main><h1>ASUS THE EYE BENCHMARK</h1>
{corpo}<script>const data={payload};
for(const key of ['scores','times']){{
  const values=data[key], max=Math.max(...Object.values(values),1);
  const root=document.getElementById(key);
  for(const [name,value] of Object.entries(values)){{
    root.innerHTML+=`<span>${{name}}: ${{value.toFixed(3)}}</span>`+
      `<div class="bar"><i style="width:${{100*value/max}}%"></i></div>`;
  }}
}}
const historyRoot=document.getElementById('history');
const historyMax=Math.max(...data.history.map(point=>point.best_score),1);
for(const point of data.history){{
  historyRoot.innerHTML+=`<span>${{point.date}}: ${{point.best_score.toFixed(3)}}</span>`+
    `<div class="bar"><i style="width:${{100*point.best_score/historyMax}}%"></i></div>`;
}}
if(!data.history.length) historyRoot.textContent='No benchmark history yet.';
</script>
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
