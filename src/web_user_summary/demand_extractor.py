from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Sequence, Tuple

from .models import DemandCandidate, DemandCluster, RedditPost

DEMAND_PATTERNS = [
    r"\bi need\b",
    r"\bi wish\b",
    r"\blooking for\b",
    r"\bdoes anyone know\b",
    r"\bany app\b",
    r"\bany tool\b",
    r"\bhow do i\b",
    r"\bstruggling with\b",
    r"\bproblem with\b",
    r"\bfrustrat(?:e|ed|ing)\b",
    r"\bwant (?:an|a) (?:app|tool|way)\b",
    r"\bthere should be\b",
]

ASK_INTENT_PATTERNS = [
    r"\bi need\b",
    r"\blooking for\b",
    r"\bdoes anyone know\b",
    r"\bneed advice\b",
    r"\bany recommendation\b",
    r"\bany app\b",
    r"\bany tool\b",
    r"\bany software\b",
    r"\bis there (?:any|a)\b",
    r"\bhow do i\b",
    r"\bcan anyone\b",
]

PRODUCT_INTENT_PATTERNS = [
    r"\bapp\b",
    r"\btool\b",
    r"\bsoftware\b",
    r"\bplatform\b",
    r"\bautomation\b",
    r"\bautomate\b",
    r"\bworkflow\b",
    r"\bintegration\b",
    r"\bplugin\b",
    r"\bdashboard\b",
    r"\bextension\b",
]

EXCLUDE_PATTERNS = [
    r"\bi will not promote\b",
    r"\blooking for (?:cofounder|co-founder|founder|partner|job)\b",
    r"\blooking for feedback\b",
    r"\broast my\b",
    r"\brate my\b",
]

SELF_PROMO_PATTERNS = [
    r"\bi built\b",
    r"\bi'm building\b",
    r"\bwe built\b",
    r"\blaunched\b",
    r"\blaunching\b",
    r"\bmvp\b",
    r"\bwaitlist\b",
    r"\bcofounder\b",
    r"\bco-founder\b",
]

URGENCY_PATTERNS = [
    r"\burgent\b",
    r"\basap\b",
    r"\bright now\b",
    r"\bimmediately\b",
    r"\bdeadline\b",
    r"\bblocked\b",
]

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "we",
    "what",
    "with",
    "you",
    "your",
}


def _compact_text(text: str) -> str:
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_sentences(text: str) -> List[str]:
    clean = _compact_text(text)
    if not clean:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]


def _normalize_phrase(text: str) -> str:
    lower = text.lower()
    lower = re.sub(r"[^a-z0-9\s]", " ", lower)
    tokens = [t for t in lower.split() if len(t) > 2 and t not in STOP_WORDS]
    # Keep a deterministic set-style view to improve fuzzy grouping across paraphrases.
    unique_tokens = sorted(set(tokens))
    return " ".join(unique_tokens[:24]).strip()


def _keyword_tokens(text: str, max_tokens: int = 8) -> List[str]:
    norm = _normalize_phrase(text)
    if not norm:
        return []
    counts = Counter(norm.split())
    return [w for w, _ in counts.most_common(max_tokens)]


def _pattern_hits(text: str, patterns: Sequence[str]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE))


def _confidence_score(title: str, body: str) -> int:
    combined = f"{title} {body}".strip()
    score = _pattern_hits(combined, DEMAND_PATTERNS)
    if "?" in combined:
        score += 1
    if re.search(r"\b(i|we)\b", combined, flags=re.IGNORECASE) and re.search(
        r"\b(need|wish|want|looking)\b", combined, flags=re.IGNORECASE
    ):
        score += 1
    if len(combined) > 220:
        score += 1
    return score


def _urgency_score(title: str, body: str) -> int:
    return _pattern_hits(f"{title} {body}", URGENCY_PATTERNS)


def _extract_best_demand_sentence(title: str, body: str) -> str:
    sentences = _split_sentences(f"{title}. {body}".strip())
    if not sentences:
        return _compact_text(title)
    for sentence in sentences:
        if _pattern_hits(sentence, DEMAND_PATTERNS) > 0:
            return sentence
    return sentences[0]


def _shorten(text: str, max_len: int = 170) -> str:
    txt = _compact_text(text)
    if len(txt) <= max_len:
        return txt
    return txt[: max_len - 3].rstrip() + "..."


def extract_demand_candidates(
    posts: Sequence[RedditPost], max_age_hours: int, min_score: int, exclude_self_promo: bool = True
) -> List[DemandCandidate]:
    now = time.time()
    cutoff = now - max_age_hours * 3600
    out: List[DemandCandidate] = []

    for post in posts:
        if post.created_utc < cutoff:
            continue
        if _pattern_hits(f"{post.title} {post.selftext}", EXCLUDE_PATTERNS) > 0:
            continue
        if exclude_self_promo and _pattern_hits(f"{post.title} {post.selftext}", SELF_PROMO_PATTERNS) > 0:
            continue
        confidence = _confidence_score(post.title, post.selftext)
        if confidence < min_score:
            continue

        demand_text = _extract_best_demand_sentence(post.title, post.selftext)
        if _pattern_hits(f"{post.title} {demand_text}", ASK_INTENT_PATTERNS) == 0:
            continue
        if _pattern_hits(f"{post.title} {demand_text}", PRODUCT_INTENT_PATTERNS) == 0:
            continue
        normalized = _normalize_phrase(demand_text or post.title)
        if not normalized:
            continue

        candidate = DemandCandidate(
            post_id=post.id,
            subreddit=post.subreddit,
            created_utc=post.created_utc,
            title=post.title,
            demand_text=_shorten(demand_text),
            normalized_text=normalized,
            confidence_score=confidence,
            urgency_score=_urgency_score(post.title, post.selftext),
            keyword_tokens=_keyword_tokens(demand_text),
            permalink=post.permalink,
            url=post.url,
        )
        out.append(candidate)

    return out


def _similarity(a: str, b: str) -> float:
    seq = SequenceMatcher(a=a, b=b).ratio()
    a_set = set(a.split())
    b_set = set(b.split())
    if not a_set or not b_set:
        return seq
    inter = len(a_set & b_set)
    union = len(a_set | b_set)
    jaccard = inter / union if union else 0.0
    return max(seq, jaccard)


def cluster_demands(candidates: Sequence[DemandCandidate], threshold: float = 0.72) -> List[DemandCluster]:
    clusters: List[DemandCluster] = []

    for candidate in sorted(candidates, key=lambda x: x.confidence_score, reverse=True):
        best_idx = -1
        best_sim = 0.0
        for idx, cluster in enumerate(clusters):
            sim = _similarity(candidate.normalized_text, cluster.normalized_anchor)
            if sim > best_sim:
                best_sim = sim
                best_idx = idx

        if best_idx >= 0 and best_sim >= threshold:
            cluster = clusters[best_idx]
            cluster.demand_count += 1
            cluster.confidence_avg += candidate.confidence_score
            cluster.urgency_avg += candidate.urgency_score
            cluster.examples.append(
                {
                    "title": candidate.title,
                    "demand_text": candidate.demand_text,
                    "subreddit": candidate.subreddit,
                    "permalink": candidate.permalink,
                    "confidence_score": candidate.confidence_score,
                    "urgency_score": candidate.urgency_score,
                }
            )
            cluster.examples = cluster.examples[:5]
            cluster.subreddits.append(candidate.subreddit)
            cluster.keywords.extend(candidate.keyword_tokens)
        else:
            cluster = DemandCluster(
                cluster_id=f"demand_{len(clusters) + 1:03d}",
                summary_demand=candidate.demand_text,
                normalized_anchor=candidate.normalized_text,
                demand_count=1,
                confidence_avg=float(candidate.confidence_score),
                urgency_avg=float(candidate.urgency_score),
                keywords=list(candidate.keyword_tokens),
                subreddits=[candidate.subreddit],
                examples=[
                    {
                        "title": candidate.title,
                        "demand_text": candidate.demand_text,
                        "subreddit": candidate.subreddit,
                        "permalink": candidate.permalink,
                        "confidence_score": candidate.confidence_score,
                        "urgency_score": candidate.urgency_score,
                    }
                ],
            )
            clusters.append(cluster)

    for cluster in clusters:
        cluster.confidence_avg = round(cluster.confidence_avg / max(cluster.demand_count, 1), 2)
        cluster.urgency_avg = round(cluster.urgency_avg / max(cluster.demand_count, 1), 2)
        cluster.subreddits = sorted(set(cluster.subreddits))
        keyword_counts = Counter(cluster.keywords)
        cluster.keywords = [word for word, _ in keyword_counts.most_common(8)]

    clusters.sort(key=lambda c: (c.demand_count, c.confidence_avg, c.urgency_avg), reverse=True)
    return clusters


def build_meta_summary(posts: Sequence[RedditPost], candidates: Sequence[DemandCandidate], clusters: Sequence[DemandCluster]) -> Dict:
    sub_counts: Dict[str, int] = defaultdict(int)
    for post in posts:
        sub_counts[post.subreddit] += 1

    return {
        "total_posts": len(posts),
        "total_candidates": len(candidates),
        "total_clusters": len(clusters),
        "subreddit_post_counts": dict(sorted(sub_counts.items(), key=lambda x: x[1], reverse=True)),
    }
