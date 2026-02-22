from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List

from .demand_extractor import build_meta_summary, cluster_demands, extract_demand_candidates
from .reddit_client import RedditClient
from .reporting import (
    build_demandsolution_seed,
    serialize_candidates,
    serialize_clusters,
    serialize_posts,
    timestamped_output_dir,
    write_json,
    write_jsonl,
    write_markdown_report,
)

DEFAULT_SUBREDDITS = "SaaS,startups,SideProject,Entrepreneur,smallbusiness,productivity,webdev"
DEFAULT_USER_AGENT = "web-user-summary/0.1 (contact: jacksuyu@gmail.com)"
DEFAULT_SEARCH_QUERIES = "need app,looking for tool,wish there was,how do i automate,any software for,struggling with"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and summarize user demand from Reddit.")
    parser.add_argument("--subreddits", default=DEFAULT_SUBREDDITS, help="Comma-separated subreddit list.")
    parser.add_argument("--sort", default="new", choices=["new", "hot", "top"], help="Reddit listing type.")
    parser.add_argument("--per-subreddit", type=int, default=80, help="Maximum posts fetched per subreddit.")
    parser.add_argument("--hours", type=int, default=168, help="Only include posts newer than this many hours.")
    parser.add_argument("--min-score", type=int, default=2, help="Minimum demand confidence score.")
    parser.add_argument("--similarity-threshold", type=float, default=0.62, help="Fuzzy grouping threshold (0-1).")
    parser.add_argument("--output-dir", default="data/reddit_requirements", help="Base output directory.")
    parser.add_argument("--user-agent", default=os.getenv("REDDIT_USER_AGENT", DEFAULT_USER_AGENT), help="HTTP User-Agent.")
    parser.add_argument("--search-queries", default=DEFAULT_SEARCH_QUERIES, help="Comma-separated query terms for /search.json.")
    parser.add_argument("--search-per-query", type=int, default=20, help="Posts fetched per query per subreddit.")
    parser.add_argument(
        "--include-self-promo",
        action="store_true",
        help="Include self-promotional founder posts (default excludes them).",
    )
    return parser.parse_args()


def parse_subreddits(raw: str) -> List[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def parse_csv_terms(raw: str) -> List[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def main() -> None:
    args = parse_args()
    subreddits = parse_subreddits(args.subreddits)
    if not subreddits:
        raise ValueError("At least one subreddit is required.")

    client = RedditClient(user_agent=args.user_agent)
    search_queries = parse_csv_terms(args.search_queries)
    all_posts = []
    for subreddit in subreddits:
        posts = client.fetch_subreddit_posts(subreddit=subreddit, sort=args.sort, limit=args.per_subreddit)
        all_posts.extend(posts)
        print(f"Fetched {len(posts):>3} posts from r/{subreddit}")
        for query in search_queries:
            q_posts = client.fetch_subreddit_search(
                subreddit=subreddit, query=query, sort=args.sort, limit=args.search_per_query
            )
            all_posts.extend(q_posts)
            print(f"  + search '{query}': {len(q_posts):>3} posts")

    # Deduplicate by post ID
    dedup = {}
    for post in all_posts:
        dedup[post.id] = post
    posts = list(dedup.values())

    candidates = extract_demand_candidates(
        posts=posts,
        max_age_hours=args.hours,
        min_score=args.min_score,
        exclude_self_promo=not args.include_self_promo,
    )
    clusters = cluster_demands(candidates=candidates, threshold=args.similarity_threshold)
    meta = build_meta_summary(posts=posts, candidates=candidates, clusters=clusters)

    out_dir = timestamped_output_dir(Path(args.output_dir))
    write_jsonl(out_dir / "raw_posts.jsonl", serialize_posts(posts))
    write_jsonl(out_dir / "demand_candidates.jsonl", serialize_candidates(candidates))
    write_json(
        out_dir / "demand_clusters.json",
        {
            "meta": meta,
            "clusters": serialize_clusters(clusters),
        },
    )
    write_json(out_dir / "demandsolution_seed_ideas.json", build_demandsolution_seed(clusters))
    write_markdown_report(out_dir / "report.md", meta=meta, clusters=clusters)

    print("")
    print(f"Saved outputs to: {out_dir}")
    print(f"Total posts: {meta['total_posts']}")
    print(f"Demand candidates: {meta['total_candidates']}")
    print(f"Demand clusters: {meta['total_clusters']}")


if __name__ == "__main__":
    main()
