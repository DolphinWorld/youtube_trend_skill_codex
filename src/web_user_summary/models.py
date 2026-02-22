from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass
class RedditPost:
    id: str
    subreddit: str
    title: str
    selftext: str
    author: str
    created_utc: float
    score: int
    num_comments: int
    upvote_ratio: float
    permalink: str
    url: str
    sort_source: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DemandCandidate:
    post_id: str
    subreddit: str
    created_utc: float
    title: str
    demand_text: str
    normalized_text: str
    confidence_score: int
    urgency_score: int
    keyword_tokens: List[str]
    permalink: str
    url: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DemandCluster:
    cluster_id: str
    summary_demand: str
    normalized_anchor: str
    demand_count: int = 0
    urgency_avg: float = 0.0
    confidence_avg: float = 0.0
    keywords: List[str] = field(default_factory=list)
    subreddits: List[str] = field(default_factory=list)
    examples: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

