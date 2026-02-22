#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish accepted Reddit requirements to markdown/html pages.")
    parser.add_argument(
        "--input-dir",
        default="",
        help="Directory under data/reddit_requirements containing llm_requirement_accepted_curated.json",
    )
    return parser.parse_args()


def latest_run_dir(base: Path) -> Path:
    dirs = [p for p in base.iterdir() if p.is_dir() and re.match(r"^\d{8}_\d{6}_utc$", p.name)]
    if not dirs:
        raise FileNotFoundError(f"No run directories found in {base}")
    return sorted(dirs, key=lambda p: p.name)[-1]


def load_accepted(input_dir: Path) -> List[Dict]:
    curated = input_dir / "llm_requirement_accepted_curated.json"
    raw = input_dir / "llm_requirement_accepted.json"
    if curated.exists():
        payload = json.loads(curated.read_text(encoding="utf-8"))
        return payload.get("accepted", [])
    if raw.exists():
        payload = json.loads(raw.read_text(encoding="utf-8"))
        return payload.get("accepted", [])
    raise FileNotFoundError(f"No accepted requirements file found in {input_dir}")


def render_markdown(run_dir: Path, accepted: List[Dict]) -> str:
    lines: List[str] = []
    lines.append("# Reddit User Requirements (LLM Curated)")
    lines.append("")
    lines.append(f"- Source run: `{run_dir.name}`")
    lines.append(f"- Generated at: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`")
    lines.append(f"- Accepted requirements: **{len(accepted)}**")
    lines.append("")
    lines.append("## Requirements")
    lines.append("")
    for idx, item in enumerate(accepted, start=1):
        cid = item.get("cluster_id", "")
        req = str(item.get("requirement", item.get("normalized_requirement", ""))).strip()
        reason = str(item.get("reason", "")).strip()
        count = item.get("demand_count", 0)
        lines.append(f"### {idx}. {req}")
        lines.append(f"- Cluster: `{cid}`")
        lines.append(f"- Mentions: {count}")
        if reason:
            lines.append(f"- Why accepted: {reason}")
        examples = item.get("examples", [])
        if examples:
            ex = examples[0]
            title = ex.get("title", "source post")
            link = ex.get("permalink", "#")
            lines.append(f"- Evidence: [{title}]({link})")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_html(run_dir: Path, accepted: List[Dict]) -> str:
    cards: List[str] = []
    for idx, item in enumerate(accepted, start=1):
        cid = item.get("cluster_id", "")
        req = str(item.get("requirement", item.get("normalized_requirement", ""))).strip()
        reason = str(item.get("reason", "")).strip()
        count = item.get("demand_count", 0)
        examples = item.get("examples", [])
        evidence_html = ""
        if examples:
            ex = examples[0]
            title = ex.get("title", "source post")
            link = ex.get("permalink", "#")
            evidence_html = f'<p class="meta">Evidence: <a href="{link}" target="_blank" rel="noreferrer">{title}</a></p>'
        cards.append(
            f"""
            <article class="card">
              <h3>{idx}. {req}</h3>
              <p class="meta">Cluster: {cid} | Mentions: {count}</p>
              <p>{reason}</p>
              {evidence_html}
            </article>
            """
        )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Reddit User Requirements</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: #121a30;
      --text: #e8eefc;
      --muted: #9cb0d8;
      --line: #2b3b63;
      --accent: #5db0ff;
    }}
    body {{ margin: 0; padding: 32px; background: linear-gradient(180deg, #0b1020, #151f38); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .wrap {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px 0; font-size: 34px; }}
    .meta {{ color: var(--muted); font-size: 14px; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 12px; margin-top: 20px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }}
    .card h3 {{ margin: 0 0 8px 0; font-size: 20px; color: #f2f6ff; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main class="wrap">
    <h1>Reddit User Requirements (LLM Curated)</h1>
    <p class="meta">Source run: {run_dir.name} | Generated: {stamp} | Accepted: {len(accepted)}</p>
    <section class="grid">
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    base = root / "data" / "reddit_requirements"
    run_dir = Path(args.input_dir) if args.input_dir else latest_run_dir(base)
    accepted = load_accepted(run_dir)

    out_dir = root / "pages" / "requirements"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "reddit_user_requirements.md"
    html_path = out_dir / "reddit_user_requirements.html"

    md_path.write_text(render_markdown(run_dir, accepted), encoding="utf-8")
    html_path.write_text(render_html(run_dir, accepted), encoding="utf-8")

    print(f"Source: {run_dir}")
    print(f"Accepted requirements: {len(accepted)}")
    print(f"Markdown page: {md_path}")
    print(f"HTML page: {html_path}")


if __name__ == "__main__":
    main()

