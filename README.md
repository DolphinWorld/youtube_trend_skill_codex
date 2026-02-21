# YouTube Trend Skill - Freshwater History Video

This workspace generates a history-style bar-chart video comparing top freshwater-consuming countries over time, with an original royalty-free soundtrack synthesized in code.

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
