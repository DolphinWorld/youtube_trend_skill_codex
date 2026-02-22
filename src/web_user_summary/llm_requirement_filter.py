from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import requests


SYSTEM_PROMPT = """You are a strict product requirement triage reviewer.

Goal:
- Keep ONLY items that are clearly user requirements for a product/software capability.

Accept ONLY when:
- It expresses a concrete need/problem and implies a software/tool/app/workflow solution.
- It is actionable enough for a product team to build against.

Reject when:
- Self-promotion, launch announcement, or "I built X".
- Hiring/cofounder/job-seeking.
- Generic discussion, opinion, storytelling, motivation, or reflection.
- Feedback/roast requests without a real user requirement.
- Too vague to infer a buildable requirement.

Return JSON only.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM-filter demand clusters to clear user requirements.")
    parser.add_argument("--input-dir", default="", help="Directory containing demand_clusters.json (default: latest in data/).")
    parser.add_argument("--batch-size", type=int, default=15)
    parser.add_argument("--provider", choices=["auto", "ollama", "openai"], default="auto")
    parser.add_argument("--ollama-model", default="qwen2.5:0.5b")
    parser.add_argument("--openai-model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    return parser.parse_args()


def latest_data_dir(base: Path) -> Path:
    dirs = [p for p in base.iterdir() if p.is_dir() and re.match(r"^\d{8}_\d{6}_utc$", p.name)]
    if not dirs:
        raise FileNotFoundError(f"No run directories found under {base}")
    return sorted(dirs, key=lambda p: p.name)[-1]


def parse_first_json(text: str) -> Dict:
    text = text.strip()
    if not text:
        raise ValueError("LLM returned empty content")
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse JSON from LLM output: {text[:200]}")
    return json.loads(match.group(0))


def build_user_prompt(items: List[Dict]) -> str:
    payload = {"items": items}
    return json.dumps(payload, ensure_ascii=False)


def call_ollama_single(model: str, item: Dict) -> Dict:
    url = "http://127.0.0.1:11434/api/chat"
    system_prompt = (
        SYSTEM_PROMPT
        + "\nFor this request, return ONE JSON object with keys:\n"
        + "cluster_id (string), accept (boolean), normalized_requirement (string), reason (string), confidence (0..1).\n"
        + "No extra keys."
    )
    body = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_predict": 400},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(item, ensure_ascii=False)},
        ],
    }
    response = requests.post(url, json=body, timeout=90)
    response.raise_for_status()
    payload = response.json()
    content = payload.get("message", {}).get("content", "")
    return parse_first_json(content)


def call_openai(model: str, items: List[Dict]) -> Dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(items)},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=body, timeout=180)
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return parse_first_json(content)


def choose_provider(requested: str) -> str:
    if requested in {"ollama", "openai"}:
        return requested
    return "openai" if os.getenv("OPENAI_API_KEY") else "ollama"


def llm_classify_all(clusters: List[Dict], provider: str, model: str, batch_size: int) -> List[Dict]:
    results: List[Dict] = []
    if provider == "openai":
        for i in range(0, len(clusters), batch_size):
            batch = clusters[i : i + batch_size]
            items = [
                {
                    "cluster_id": c.get("cluster_id"),
                    "summary_demand": c.get("summary_demand", ""),
                    "keywords": c.get("keywords", []),
                    "mention_count": c.get("demand_count", 0),
                    "examples": c.get("examples", [])[:2],
                }
                for c in batch
            ]
            payload = call_openai(model=model, items=items)
            batch_results = payload.get("results", payload.get("items", []))
            if not isinstance(batch_results, list):
                raise RuntimeError(f"Unexpected LLM payload: {payload}")
            results.extend(batch_results)
    else:
        total = len(clusters)
        for idx, c in enumerate(clusters, start=1):
            item = {
                "cluster_id": c.get("cluster_id"),
                "summary_demand": c.get("summary_demand", ""),
                "keywords": c.get("keywords", []),
                "mention_count": c.get("demand_count", 0),
                "examples": c.get("examples", [])[:2],
            }
            print(f"LLM reviewing {idx}/{total} - {item['cluster_id']}", flush=True)
            results.append(call_ollama_single(model=model, item=item))
    return results


def render_review_md(path: Path, accepted: List[Dict], rejected: List[Dict]) -> None:
    lines: List[str] = []
    lines.append("# LLM Requirement Review")
    lines.append("")
    lines.append(f"- Accepted: {len(accepted)}")
    lines.append(f"- Rejected: {len(rejected)}")
    lines.append("")
    lines.append("## Accepted")
    for idx, item in enumerate(accepted, start=1):
        lines.append(f"{idx}. `{item['cluster_id']}` - {item.get('normalized_requirement', '').strip()}")
        lines.append(f"   - reason: {item.get('reason', '')}")
        lines.append(f"   - confidence: {item.get('confidence', 0)}")
    lines.append("")
    lines.append("## Rejected")
    for idx, item in enumerate(rejected, start=1):
        lines.append(f"{idx}. `{item['cluster_id']}` - {item.get('reason', '')}")
        lines.append(f"   - confidence: {item.get('confidence', 0)}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def normalize_result(result: Dict) -> Dict:
    accept_raw = result.get("accept", False)
    if isinstance(accept_raw, bool):
        accept = accept_raw
    elif isinstance(accept_raw, (int, float)):
        accept = bool(accept_raw)
    else:
        accept = str(accept_raw).strip().lower() in {"true", "yes", "accept", "accepted", "1"}

    conf_raw = result.get("confidence", result.get("confidence_score", 0.0))
    try:
        confidence = float(conf_raw)
    except Exception:
        confidence = 0.0
    if confidence > 1.0:
        confidence = min(1.0, confidence / 10.0)

    return {
        "cluster_id": str(result.get("cluster_id", "")).strip(),
        "accept": accept,
        "normalized_requirement": str(result.get("normalized_requirement", "")).strip(),
        "reason": str(result.get("reason", "")).strip(),
        "confidence": confidence,
    }


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    base_data = root / "data" / "reddit_requirements"
    input_dir = Path(args.input_dir) if args.input_dir else latest_data_dir(base_data)
    clusters_path = input_dir / "demand_clusters.json"

    if not clusters_path.exists():
        raise FileNotFoundError(f"Missing {clusters_path}")

    obj = json.loads(clusters_path.read_text(encoding="utf-8"))
    clusters = obj.get("clusters", [])
    if not isinstance(clusters, list) or not clusters:
        raise RuntimeError(f"No clusters found in {clusters_path}")

    provider = choose_provider(args.provider)
    model = args.openai_model if provider == "openai" else args.ollama_model

    raw_results = llm_classify_all(clusters=clusters, provider=provider, model=model, batch_size=args.batch_size)
    cleaned = [normalize_result(r) for r in raw_results if r.get("cluster_id")]

    # Ensure one output row per cluster, default to reject if missing.
    by_id = {r["cluster_id"]: r for r in cleaned}
    final_results: List[Dict] = []
    for c in clusters:
        cid = str(c.get("cluster_id", "")).strip()
        if cid in by_id:
            final_results.append(by_id[cid])
        else:
            final_results.append(
                {
                    "cluster_id": cid,
                    "accept": False,
                    "normalized_requirement": "",
                    "reason": "No classifier output for this cluster",
                    "confidence": 0.0,
                }
            )

    cluster_lookup = {c.get("cluster_id"): c for c in clusters}
    accepted = [r for r in final_results if r["accept"]]
    rejected = [r for r in final_results if not r["accept"]]

    accepted_enriched = []
    for r in accepted:
        c = cluster_lookup.get(r["cluster_id"], {})
        item = dict(r)
        item["demand_count"] = c.get("demand_count", 0)
        item["summary_demand"] = c.get("summary_demand", "")
        item["keywords"] = c.get("keywords", [])
        item["examples"] = c.get("examples", [])[:3]
        accepted_enriched.append(item)

    review_path = input_dir / "llm_requirement_review.json"
    accepted_path = input_dir / "llm_requirement_accepted.json"
    report_path = input_dir / "llm_requirement_review.md"

    review_payload = {
        "provider": provider,
        "model": model,
        "input_dir": str(input_dir),
        "total_clusters": len(clusters),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "results": final_results,
    }
    review_path.write_text(json.dumps(review_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    accepted_path.write_text(json.dumps({"accepted": accepted_enriched}, indent=2, ensure_ascii=False), encoding="utf-8")
    render_review_md(report_path, accepted=accepted, rejected=rejected)

    print(f"Input directory: {input_dir}")
    print(f"Provider/model: {provider}/{model}")
    print(f"Accepted: {len(accepted)} / {len(clusters)}")
    print("")
    print("Accepted requirements:")
    for idx, item in enumerate(accepted_enriched, start=1):
        print(f"{idx:>2}. [{item['cluster_id']}] {item['normalized_requirement']}")
        print(f"    mentions={item['demand_count']} confidence={item['confidence']:.2f}")
        if item.get("reason"):
            print(f"    reason: {item['reason']}")

    print("")
    print(f"Saved review: {review_path}")
    print(f"Saved accepted: {accepted_path}")
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
