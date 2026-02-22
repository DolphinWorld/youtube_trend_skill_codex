#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-post curated social requirements to DemandSolution.")
    parser.add_argument(
        "--site-url",
        default="https://jacksuyu-demandsolution-codex.hf.space",
        help="Base URL of deployed DemandSolution site.",
    )
    parser.add_argument(
        "--input-dir",
        default="",
        help="Run directory with llm_requirement_accepted_curated.json (default: latest under data/reddit_requirements).",
    )
    parser.add_argument(
        "--state-file",
        default="data/reddit_requirements/posting_state.json",
        help="Path to posting state file for dedupe.",
    )
    parser.add_argument("--timeout-s", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def latest_run_dir(base: Path) -> Path:
    runs = sorted([p for p in base.iterdir() if p.is_dir() and p.name.endswith("_utc")], key=lambda p: p.name)
    if not runs:
        raise FileNotFoundError(f"No run directories found in {base}")
    return runs[-1]


def load_accepted_requirements(run_dir: Path) -> List[Dict]:
    curated = run_dir / "llm_requirement_accepted_curated.json"
    raw = run_dir / "llm_requirement_accepted.json"
    if curated.exists():
        return json.loads(curated.read_text(encoding="utf-8")).get("accepted", [])
    if raw.exists():
        return json.loads(raw.read_text(encoding="utf-8")).get("accepted", [])
    raise FileNotFoundError(f"No accepted requirements JSON found in {run_dir}")


def load_state(path: Path) -> Dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"anon_id": str(uuid.uuid4()), "posted_keys": {}, "runs": []}


def save_state(path: Path, state: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def requirement_key(item: Dict) -> str:
    material = "|".join(
        [
            str(item.get("cluster_id", "")),
            str(item.get("requirement", item.get("normalized_requirement", ""))),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_raw_input_text(item: Dict) -> str:
    requirement = str(item.get("requirement", item.get("normalized_requirement", ""))).strip()
    reason = str(item.get("reason", "")).strip()
    mentions = item.get("demand_count", 1)
    examples = item.get("examples", [])
    source_link = ""
    source_title = ""
    if examples:
        source_link = str(examples[0].get("permalink", "")).strip()
        source_title = str(examples[0].get("title", "")).strip()

    lines = [
        f"User requirement from social community: {requirement}",
        "",
        "Context:",
        f"- Source: Reddit",
        f"- Mention count in this run: {mentions}",
    ]
    if reason:
        lines.append(f"- LLM acceptance reason: {reason}")
    if source_title:
        lines.append(f"- Evidence title: {source_title}")
    if source_link:
        lines.append(f"- Evidence link: {source_link}")
    lines.append("")
    lines.append("Please generate a buildable product spec from this requirement.")
    text = "\n".join(lines).strip()
    if len(text) < 20:
        text = (text + " " + requirement).strip()
    return text[:2900]


def post_idea(session: requests.Session, site_url: str, anon_id: str, payload: Dict, timeout_s: int) -> Tuple[int, Dict]:
    endpoint = site_url.rstrip("/") + "/api/ideas"
    headers = {"x-anon-id": anon_id, "Content-Type": "application/json"}
    resp = session.post(endpoint, headers=headers, json=payload, timeout=timeout_s)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text[:600]}
    return resp.status_code, body


def render_report(run_dir: Path, results: List[Dict]) -> None:
    out_json = run_dir / "posted_to_demandsolution.json"
    out_md = run_dir / "posted_to_demandsolution.md"
    out_json.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Posted Requirements to DemandSolution",
        "",
        f"- Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- Total processed: {len(results)}",
        f"- Posted/merged: {sum(1 for r in results if r['status'] in {'posted', 'merged', 'already_posted'})}",
        "",
        "## Details",
        "",
    ]
    for idx, result in enumerate(results, start=1):
        lines.append(f"{idx}. `{result['cluster_id']}` - **{result['status']}**")
        lines.append(f"   - requirement: {result['requirement']}")
        if result.get("message"):
            lines.append(f"   - message: {result['message']}")
        if result.get("idea_id"):
            lines.append(f"   - idea_id: `{result['idea_id']}`")
    out_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    base_data = root / "data" / "reddit_requirements"
    run_dir = Path(args.input_dir) if args.input_dir else latest_run_dir(base_data)
    state_file = root / args.state_file if not Path(args.state_file).is_absolute() else Path(args.state_file)

    accepted = load_accepted_requirements(run_dir)
    state = load_state(state_file)
    anon_id = state.get("anon_id") or str(uuid.uuid4())
    state["anon_id"] = anon_id
    posted_keys = state.setdefault("posted_keys", {})
    results: List[Dict] = []

    session = requests.Session()
    session.headers.update({"User-Agent": "youtube-trend-skill-codex/requirements-poster/0.1"})
    try:
        session.get(args.site_url.rstrip("/") + "/", timeout=min(20, args.timeout_s))
    except Exception:
        pass

    for item in accepted:
        cluster_id = str(item.get("cluster_id", ""))
        requirement = str(item.get("requirement", item.get("normalized_requirement", ""))).strip()
        key = requirement_key(item)
        if key in posted_keys:
            results.append(
                {
                    "cluster_id": cluster_id,
                    "requirement": requirement,
                    "status": "already_posted",
                    "idea_id": posted_keys[key].get("idea_id"),
                    "message": "Skipped because this requirement key already exists in posting_state.",
                }
            )
            continue

        payload = {
            "raw_input_text": build_raw_input_text(item),
            "target_users": "People asking for practical productivity and workflow software tools",
            "platform": "Any",
            "constraints": "Prefer simple setup and low friction.",
            "source_tag": "_social_",
            "show_name": False,
        }

        if args.dry_run:
            results.append(
                {
                    "cluster_id": cluster_id,
                    "requirement": requirement,
                    "status": "dry_run",
                    "message": "Prepared payload only; not submitted.",
                }
            )
            continue

        status, body = post_idea(session, args.site_url, anon_id, payload, args.timeout_s)

        if status == 201:
            idea_id = body.get("idea", {}).get("id")
            posted_keys[key] = {"idea_id": idea_id, "cluster_id": cluster_id, "posted_at": datetime.now(timezone.utc).isoformat()}
            results.append(
                {
                    "cluster_id": cluster_id,
                    "requirement": requirement,
                    "status": "posted",
                    "idea_id": idea_id,
                    "message": "Created new idea.",
                }
            )
        elif status == 200 and body.get("merged"):
            idea_id = body.get("idea", {}).get("id")
            posted_keys[key] = {"idea_id": idea_id, "cluster_id": cluster_id, "posted_at": datetime.now(timezone.utc).isoformat()}
            results.append(
                {
                    "cluster_id": cluster_id,
                    "requirement": requirement,
                    "status": "merged",
                    "idea_id": idea_id,
                    "message": body.get("message", "Merged into existing idea."),
                }
            )
        else:
            results.append(
                {
                    "cluster_id": cluster_id,
                    "requirement": requirement,
                    "status": "failed",
                    "message": f"HTTP {status}: {body}",
                }
            )

    state.setdefault("runs", []).append(
        {
            "run_dir": str(run_dir),
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "results_count": len(results),
            "posted_count": sum(1 for r in results if r["status"] in {"posted", "merged"}),
        }
    )

    save_state(state_file, state)
    render_report(run_dir, results)

    print(f"Source run: {run_dir}")
    print(f"Target site: {args.site_url}")
    print(f"Processed requirements: {len(results)}")
    print(f"Posted or merged: {sum(1 for r in results if r['status'] in {'posted', 'merged', 'already_posted'})}")
    print(f"State file: {state_file}")
    print(f"Report JSON: {run_dir / 'posted_to_demandsolution.json'}")
    print(f"Report MD: {run_dir / 'posted_to_demandsolution.md'}")

    for idx, result in enumerate(results, start=1):
        print(f"{idx:>2}. [{result['cluster_id']}] {result['status']} - {result['requirement'][:120]}")


if __name__ == "__main__":
    main()
