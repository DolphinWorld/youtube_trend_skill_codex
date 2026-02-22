from __future__ import annotations

import time
from typing import Dict, List, Optional

import requests

from .models import RedditPost


class RedditClient:
    def __init__(self, user_agent: str, timeout_s: int = 20, max_retries: int = 4) -> None:
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
            }
        )

    def _request_json(self, url: str, params: Dict) -> Dict:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout_s)
                if response.status_code == 429:
                    sleep_s = min(12, 2 * attempt)
                    time.sleep(sleep_s)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.3 * attempt)
                else:
                    raise RuntimeError(f"Reddit request failed after retries: {url}") from last_error
        raise RuntimeError(f"Unexpected request failure: {url}")

    def fetch_subreddit_posts(self, subreddit: str, sort: str = "new", limit: int = 100) -> List[RedditPost]:
        if sort not in {"new", "hot", "top"}:
            raise ValueError("sort must be one of: new, hot, top")

        out: List[RedditPost] = []
        after: Optional[str] = None
        remaining = max(1, limit)

        while remaining > 0:
            page_limit = min(100, remaining)
            params = {"limit": page_limit, "raw_json": 1}
            if after:
                params["after"] = after

            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
            payload = self._request_json(url, params=params)
            data = payload.get("data", {})
            children = data.get("children", [])

            for child in children:
                item = child.get("data", {})
                post = RedditPost(
                    id=str(item.get("id", "")),
                    subreddit=str(item.get("subreddit", subreddit)),
                    title=str(item.get("title", "")).strip(),
                    selftext=str(item.get("selftext", "")).strip(),
                    author=str(item.get("author", "")),
                    created_utc=float(item.get("created_utc", 0.0)),
                    score=int(item.get("score", 0)),
                    num_comments=int(item.get("num_comments", 0)),
                    upvote_ratio=float(item.get("upvote_ratio", 0.0) or 0.0),
                    permalink=f"https://www.reddit.com{item.get('permalink', '')}",
                    url=str(item.get("url", "")),
                    sort_source=sort,
                )
                if post.id and post.title:
                    out.append(post)

            after = data.get("after")
            if not after or not children:
                break
            remaining -= len(children)
            time.sleep(0.6)

        return out

    def fetch_subreddit_search(self, subreddit: str, query: str, sort: str = "new", limit: int = 50) -> List[RedditPost]:
        out: List[RedditPost] = []
        after: Optional[str] = None
        remaining = max(1, limit)

        while remaining > 0:
            page_limit = min(100, remaining)
            params = {
                "q": query,
                "restrict_sr": "1",
                "sort": sort,
                "limit": page_limit,
                "raw_json": 1,
            }
            if after:
                params["after"] = after

            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            payload = self._request_json(url, params=params)
            data = payload.get("data", {})
            children = data.get("children", [])

            for child in children:
                item = child.get("data", {})
                post = RedditPost(
                    id=str(item.get("id", "")),
                    subreddit=str(item.get("subreddit", subreddit)),
                    title=str(item.get("title", "")).strip(),
                    selftext=str(item.get("selftext", "")).strip(),
                    author=str(item.get("author", "")),
                    created_utc=float(item.get("created_utc", 0.0)),
                    score=int(item.get("score", 0)),
                    num_comments=int(item.get("num_comments", 0)),
                    upvote_ratio=float(item.get("upvote_ratio", 0.0) or 0.0),
                    permalink=f"https://www.reddit.com{item.get('permalink', '')}",
                    url=str(item.get("url", "")),
                    sort_source=f"search:{query}",
                )
                if post.id and post.title:
                    out.append(post)

            after = data.get("after")
            if not after or not children:
                break
            remaining -= len(children)
            time.sleep(0.6)

        return out
