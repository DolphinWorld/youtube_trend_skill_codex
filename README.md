# YouTube Trend Skill - Freshwater History Video

This workspace generates a history-style bar-chart video comparing top freshwater-consuming countries over time, with an original royalty-free soundtrack synthesized in code.

It also includes a Reddit-first requirement mining pipeline to collect and publish user demand signals for product planning.

## Output Files
- `/Users/jacksu/projects/youtube_trend_skill_codex/outputs/freshwater_top_countries_history.mp4`
- `/Users/jacksu/projects/youtube_trend_skill_codex/outputs/freshwater_top_countries_history_silent.mp4`
- `/Users/jacksu/projects/youtube_trend_skill_codex/outputs/freshwater_history_urgent_soundtrack.wav`

## Data Source
- `/Users/jacksu/projects/youtube_trend_skill_codex/data/annual-freshwater-withdrawals/annual-freshwater-withdrawals.csv`

## Generate Video
```bash
cd /Users/jacksu/projects/youtube_trend_skill_codex
python3 -m pip install --user -r requirements.txt
python3 scripts/build_freshwater_history_video.py
```

## Notes
- Chart uses country ISO3 rows only (aggregates removed).
- Units displayed: `km^3/year`.
- Soundtrack is procedurally synthesized to avoid licensing issues.
- You can tune pacing with `FPS`, `FRAMES_PER_YEAR`, and intro/outro constants in `scripts/build_freshwater_history_video.py`.

## User Requirement Mining (Reddit)

### Collect + summarize requirements
```bash
cd /Users/jacksu/projects/youtube_trend_skill_codex
python3 -m pip install --user -r requirements.txt
python3 -m src.web_user_summary.cli \
  --subreddits SaaS,startups,SideProject,Entrepreneur,smallbusiness,productivity,webdev \
  --sort new \
  --per-subreddit 80 \
  --search-per-query 20 \
  --hours 168
```

### Optional LLM review (local Ollama)
```bash
python3 -m src.web_user_summary.llm_requirement_filter \
  --input-dir /Users/jacksu/projects/youtube_trend_skill_codex/data/reddit_requirements/20260222_154256_utc \
  --provider ollama \
  --ollama-model qwen2.5:0.5b
```

### Publish requirements pages
```bash
python3 scripts/publish_requirements_page.py \
  --input-dir /Users/jacksu/projects/youtube_trend_skill_codex/data/reddit_requirements/20260222_154256_utc
```

Published pages:
- `/Users/jacksu/projects/youtube_trend_skill_codex/pages/requirements/reddit_user_requirements.md`
- `/Users/jacksu/projects/youtube_trend_skill_codex/pages/requirements/reddit_user_requirements.html`

### Auto-post accepted requirements to live DemandSolution
```bash
python3 scripts/post_requirements_to_demandsolution.py \
  --site-url https://jacksuyu-demandsolution-codex.hf.space/ \
  --input-dir /Users/jacksu/projects/youtube_trend_skill_codex/data/reddit_requirements/20260222_154256_utc
```

This writes:
- posting state: `/Users/jacksu/projects/youtube_trend_skill_codex/data/reddit_requirements/posting_state.json`
- posting report: `/Users/jacksu/projects/youtube_trend_skill_codex/data/reddit_requirements/<run>/posted_to_demandsolution.md`

## Daily Automation (GitHub Actions)

A scheduled workflow runs daily and can also be triggered manually:
- workflow file: `/Users/jacksu/projects/youtube_trend_skill_codex/.github/workflows/daily-social-requirements.yml`
- schedule: daily at 13:15 UTC

Required repository settings:
- Secret: `OPENAI_API_KEY`
- Variable: `DEMANDSOLUTION_SITE_URL` (example: `https://jacksuyu-demandsolution-codex.hf.space/`)

What it does each run:
1. Collects fresh Reddit posts.
2. Filters to clear requirements with OpenAI.
3. Regenerates requirements pages.
4. Auto-posts accepted requirements to DemandSolution (with `_social_` tag).
5. Commits updated pages and posting state back to the repo.
