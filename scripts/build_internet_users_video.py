#!/usr/bin/env python3
"""Generate a historical top-country Internet users video with real music."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import imageio.v2 as imageio
import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_DATA = [
    ROOT / "data" / "number-of-internet-users.csv",
    ROOT / "data" / "internet_user" / "number-of-internet-users.csv",
]

OUT_DIR = ROOT / "outputs"
OUT_VIDEO_SILENT = OUT_DIR / "internet_users_top_countries_history_silent.mp4"
OUT_VIDEO_FINAL = OUT_DIR / "internet_users_top_countries_history.mp4"

# Pick a real downloaded track with a modern/historical documentary tone.
MUSIC_TRACK = ROOT / "assets" / "music" / "Horizons - Alex Jones _ Xander Jones.mp3"

FPS = 24
FRAMES_PER_YEAR = 10
TOP_N = 12
INTRO_SECONDS = 2.0
OUTRO_SECONDS = 2.2


def pick_data_file() -> Path:
    for p in CANDIDATE_DATA:
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not find number-of-internet-users.csv under: {CANDIDATE_DATA}")


def load_country_timeseries() -> pd.DataFrame:
    data_csv = pick_data_file()
    df = pd.read_csv(data_csv)
    value_col = [col for col in df.columns if col not in ("Entity", "Code", "Year")][0]

    countries = df[df["Code"].fillna("").str.len() == 3].copy()
    countries = countries[["Entity", "Year", value_col]].rename(columns={value_col: "internet_users"})

    pivot = countries.pivot_table(index="Year", columns="Entity", values="internet_users", aggfunc="mean")
    years = np.arange(int(pivot.index.min()), int(pivot.index.max()) + 1)
    pivot = pivot.reindex(years)
    pivot = pivot.interpolate(axis=0, limit_direction="both").fillna(0.0)

    # Convert to millions of users for readable axis labels.
    pivot = pivot / 1e6
    pivot = pivot.loc[:, pivot.max(axis=0) > 0.01]
    return pivot


def make_color_map(columns: list[str]) -> dict[str, tuple[float, float, float, float]]:
    cmap = plt.get_cmap("tab20")
    return {country: cmap(i % 20) for i, country in enumerate(columns)}


def style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor("#0b1220")
    ax.grid(axis="x", color="#334155", alpha=0.35, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors="#e2e8f0", labelsize=11)


def draw_intro(ax: plt.Axes, width_hint: float) -> None:
    style_axis(ax)
    ax.set_xlim(0, max(width_hint, 1))
    ax.set_ylim(-1, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(
        0.02,
        0.72,
        "Global Internet Adoption",
        transform=ax.transAxes,
        color="#f8fafc",
        fontsize=42,
        fontweight="bold",
        ha="left",
    )
    ax.text(
        0.02,
        0.50,
        "Top countries by number of Internet users\nacross 1990-2021",
        transform=ax.transAxes,
        color="#cbd5e1",
        fontsize=22,
        ha="left",
    )
    ax.text(
        0.02,
        0.22,
        "Unit: million users | Source: OWID historical series",
        transform=ax.transAxes,
        color="#94a3b8",
        fontsize=13,
        ha="left",
    )


def draw_outro(ax: plt.Axes, width_hint: float) -> None:
    style_axis(ax)
    ax.set_xlim(0, max(width_hint, 1))
    ax.set_ylim(-1, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(
        0.02,
        0.64,
        "Connectivity grew fast,",
        transform=ax.transAxes,
        color="#f8fafc",
        fontsize=34,
        fontweight="bold",
        ha="left",
    )
    ax.text(
        0.02,
        0.46,
        "but access gaps still remain.",
        transform=ax.transAxes,
        color="#f8fafc",
        fontsize=34,
        fontweight="bold",
        ha="left",
    )
    ax.text(
        0.02,
        0.20,
        "Future growth should be inclusive, affordable, and resilient.",
        transform=ax.transAxes,
        color="#cbd5e1",
        fontsize=16,
        ha="left",
    )


def draw_year_frame(
    ax: plt.Axes,
    data: pd.DataFrame,
    colors: dict[str, tuple[float, float, float, float]],
    frame_idx: int,
) -> None:
    years = data.index.to_numpy()
    start_year = int(years.min())
    end_year = int(years.max())

    year_float = start_year + frame_idx / FRAMES_PER_YEAR
    year_float = min(year_float, float(end_year))

    y0 = int(math.floor(year_float))
    y1 = min(end_year, y0 + 1)
    alpha = year_float - y0

    v0 = data.loc[y0]
    v1 = data.loc[y1]
    values = v0 * (1 - alpha) + v1 * alpha

    top = values.nlargest(TOP_N).sort_values(ascending=True)

    style_axis(ax)

    max_x = max(1.0, float(top.max()) * 1.12)
    ax.set_xlim(0, max_x)
    ax.set_ylim(-0.8, len(top) - 0.2)

    y_pos = np.arange(len(top))
    bar_colors = [colors[country] for country in top.index]
    ax.barh(y_pos, top.values, color=bar_colors, alpha=0.92, edgecolor="#020617", linewidth=0.5)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(top.index, color="#e2e8f0", fontsize=12)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:,.0f}"))

    for i, (_country, value) in enumerate(top.items()):
        ax.text(value + max_x * 0.008, i, f"{value:,.1f}", va="center", ha="left", color="#f8fafc", fontsize=10)

    ax.set_title(
        "Top Countries by Number of Internet Users",
        color="#f8fafc",
        fontsize=24,
        pad=16,
        fontweight="bold",
    )
    ax.text(
        0.01,
        0.96,
        "Unit: million users (country-level)",
        transform=ax.transAxes,
        color="#94a3b8",
        fontsize=11,
        ha="left",
        va="top",
    )
    ax.text(
        0.995,
        0.96,
        f"Year {year_float:0.1f}",
        transform=ax.transAxes,
        color="#f8fafc",
        fontsize=28,
        fontweight="bold",
        ha="right",
        va="top",
    )


def render_video(data: pd.DataFrame) -> float:
    years_count = int(data.index.max() - data.index.min() + 1)
    main_frames = years_count * FRAMES_PER_YEAR
    intro_frames = int(round(INTRO_SECONDS * FPS))
    outro_frames = int(round(OUTRO_SECONDS * FPS))
    total_frames = intro_frames + main_frames + outro_frames
    duration_seconds = total_frames / FPS

    colors = make_color_map(data.columns.tolist())

    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
    fig.patch.set_facecolor("#070d17")
    plt.subplots_adjust(left=0.21, right=0.96, top=0.90, bottom=0.08)

    with imageio.get_writer(OUT_VIDEO_SILENT, fps=FPS, codec="libx264", quality=8) as writer:
        for frame in range(total_frames):
            ax.clear()

            if frame < intro_frames:
                draw_intro(ax, float(data.max().max()))
            elif frame >= intro_frames + main_frames:
                draw_outro(ax, float(data.max().max()))
            else:
                draw_year_frame(ax, data, colors, frame - intro_frames)

            fig.canvas.draw()
            frame_rgba = np.asarray(fig.canvas.buffer_rgba())
            writer.append_data(frame_rgba[:, :, :3])

    plt.close(fig)
    return duration_seconds


def remux_music(duration_s: float) -> None:
    if not MUSIC_TRACK.exists():
        raise FileNotFoundError(f"Music track not found: {MUSIC_TRACK}")

    fade_out_start = max(0.0, duration_s - 2.2)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(OUT_VIDEO_SILENT),
        "-i",
        str(MUSIC_TRACK),
        "-filter:a",
        f"atrim=0:{duration_s:.3f},afade=t=in:st=0:d=1.4,afade=t=out:st={fade_out_start:.3f}:d=2.0,volume=0.64",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(OUT_VIDEO_FINAL),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_country_timeseries()
    duration = render_video(data)
    remux_music(duration)

    print(f"Created: {OUT_VIDEO_FINAL}")
    print(f"Silent video: {OUT_VIDEO_SILENT}")
    print(f"Music track: {MUSIC_TRACK}")


if __name__ == "__main__":
    main()
