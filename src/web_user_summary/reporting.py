from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from .models import DemandCandidate, DemandCluster, RedditPost


def timestamped_output_dir(base_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_utc")
    out = base_dir / stamp
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_jsonl(path: Path, rows: Iterable[Dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown_report(path: Path, meta: Dict, clusters: List[DemandCluster], top_n: int = 25) -> None:
    lines: List[str] = []
    lines.append("# Reddit User Demand Summary")
    lines.append("")
    lines.append("## Run Metrics")
    lines.append(f"- Total posts scanned: {meta.get('total_posts', 0)}")
    lines.append(f"- Demand candidates: {meta.get('total_candidates', 0)}")
    lines.append(f"- Demand clusters: {meta.get('total_clusters', 0)}")
    lines.append("")
    lines.append("## Subreddit Coverage")
    for sub, count in meta.get("subreddit_post_counts", {}).items():
        lines.append(f"- r/{sub}: {count} posts")
    lines.append("")
    lines.append("## Top Demand Themes")

    for idx, cluster in enumerate(clusters[:top_n], start=1):
        lines.append(f"### {idx}. {cluster.summary_demand}")
        lines.append(f"- Cluster ID: `{cluster.cluster_id}`")
        lines.append(f"- Mentions: {cluster.demand_count}")
        lines.append(f"- Avg confidence: {cluster.confidence_avg}")
        lines.append(f"- Avg urgency: {cluster.urgency_avg}")
        lines.append(f"- Subreddits: {', '.join(cluster.subreddits)}")
        lines.append(f"- Keywords: {', '.join(cluster.keywords)}")
        if cluster.examples:
            ex = cluster.examples[0]
            lines.append(f"- Example post: [{ex.get('title', 'post')}]({ex.get('permalink', '#')})")
        lines.append("")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def serialize_posts(posts: Iterable[RedditPost]) -> List[Dict]:
    return [p.to_dict() for p in posts]


def serialize_candidates(candidates: Iterable[DemandCandidate]) -> List[Dict]:
    return [c.to_dict() for c in candidates]


def serialize_clusters(clusters: Iterable[DemandCluster]) -> List[Dict]:
    return [c.to_dict() for c in clusters]


def _title_from_demand(text: str) -> str:
    clean = " ".join(text.strip().split())
    if not clean:
        return "Community demand"
    clean = clean.rstrip(".?!")
    words = clean.split()
    if len(words) <= 12:
        return clean[:1].upper() + clean[1:]
    short = " ".join(words[:12]).rstrip(",;:")
    return short[:1].upper() + short[1:] + "..."


def build_demandsolution_seed(clusters: List[DemandCluster], source_name: str = "reddit") -> Dict:
    ideas: List[Dict] = []
    for cluster in clusters:
        ideas.append(
            {
                "source": source_name,
                "source_cluster_id": cluster.cluster_id,
                "title": _title_from_demand(cluster.summary_demand),
                "problem_statement": cluster.summary_demand,
                "tags": cluster.keywords[:6],
                "signal_strength": {
                    "mention_count": cluster.demand_count,
                    "confidence_avg": cluster.confidence_avg,
                    "urgency_avg": cluster.urgency_avg,
                    "subreddits": cluster.subreddits,
                },
                "evidence_posts": cluster.examples[:5],
            }
        )
    return {"ideas": ideas}
