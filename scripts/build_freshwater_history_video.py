#!/usr/bin/env python3
"""Generate a historical top-country freshwater withdrawal video with soundtrack."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import imageio.v2 as imageio
import imageio_ffmpeg
import matplotlib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
from scipy.io import wavfile

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = ROOT / "data" / "annual-freshwater-withdrawals" / "annual-freshwater-withdrawals.csv"
OUT_DIR = ROOT / "outputs"
OUT_VIDEO_SILENT = OUT_DIR / "freshwater_top_countries_history_silent.mp4"
OUT_AUDIO = OUT_DIR / "freshwater_history_urgent_soundtrack.wav"
OUT_VIDEO_FINAL = OUT_DIR / "freshwater_top_countries_history.mp4"

FPS = 24
FRAMES_PER_YEAR = 8
TOP_N = 12
INTRO_SECONDS = 2.0
OUTRO_SECONDS = 2.5


def load_country_timeseries() -> pd.DataFrame:
    df = pd.read_csv(DATA_CSV)
    value_col = [col for col in df.columns if col not in ("Entity", "Code", "Year")][0]

    # Keep ISO3 country rows only to avoid regional/income aggregates.
    countries = df[df["Code"].fillna("").str.len() == 3].copy()
    countries = countries[["Entity", "Year", value_col]]
    countries = countries.rename(columns={value_col: "withdrawals_m3"})

    pivot = countries.pivot_table(index="Year", columns="Entity", values="withdrawals_m3", aggfunc="mean")
    years = np.arange(int(pivot.index.min()), int(pivot.index.max()) + 1)
    pivot = pivot.reindex(years)
    pivot = pivot.interpolate(axis=0, limit_direction="both").fillna(0.0)

    # Convert to km^3/year for cleaner chart scale.
    pivot = pivot / 1e9
    pivot = pivot.loc[:, pivot.max(axis=0) > 0.0]
    return pivot


def make_color_map(columns: list[str]) -> dict[str, tuple[float, float, float, float]]:
    cmap = plt.get_cmap("tab20")
    return {country: cmap(i % 20) for i, country in enumerate(columns)}


def style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor("#0f1720")
    ax.grid(axis="x", color="#334155", alpha=0.35, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors="#e2e8f0", labelsize=11)


def draw_intro(ax: plt.Axes, width_hint: float) -> None:
    _ = width_hint
    panel = dict(boxstyle="round,pad=0.55", facecolor="#020617", edgecolor="#334155", alpha=0.84)
    ax.text(
        0.02,
        0.93,
        "Freshwater Under Pressure",
        transform=ax.transAxes,
        color="#f8fafc",
        fontsize=28,
        fontweight="bold",
        ha="left",
        va="top",
        bbox=panel,
    )
    ax.text(
        0.02,
        0.82,
        "Top freshwater-withdrawing countries across 1962-2022",
        transform=ax.transAxes,
        color="#cbd5e1",
        fontsize=14,
        ha="left",
        va="top",
    )
    ax.text(
        0.02,
        0.75,
        "Data: OWID | Unit: km^3/year",
        transform=ax.transAxes,
        color="#94a3b8",
        fontsize=11,
        ha="left",
        va="top",
    )


def draw_outro(ax: plt.Axes, width_hint: float) -> None:
    _ = width_hint
    panel = dict(boxstyle="round,pad=0.55", facecolor="#020617", edgecolor="#334155", alpha=0.84)
    ax.text(
        0.02,
        0.91,
        "Act early: protect water and reduce waste.",
        transform=ax.transAxes,
        color="#f8fafc",
        fontsize=24,
        fontweight="bold",
        ha="left",
        va="top",
        bbox=panel,
    )
    ax.text(
        0.02,
        0.79,
        "Solutions must be local, urgent, and sustained.",
        transform=ax.transAxes,
        color="#cbd5e1",
        fontsize=13,
        ha="left",
        va="top",
    )


def draw_year_frame(
    ax: plt.Axes,
    data: pd.DataFrame,
    colors: dict[str, tuple[float, float, float, float]],
    frame_idx: int,
) -> None:
    years = data.index.to_numpy()
    start_year = years.min()
    end_year = years.max()

    year_float = start_year + frame_idx / FRAMES_PER_YEAR
    year_float = min(year_float, float(end_year))

    y0 = int(math.floor(year_float))
    y1 = int(min(end_year, y0 + 1))
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
        "Top Countries by Annual Freshwater Withdrawals",
        color="#f8fafc",
        fontsize=24,
        pad=16,
        fontweight="bold",
    )
    ax.text(
        0.01,
        0.96,
        "Unit: km^3/year (country-level)",
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
    years_count = data.index.max() - data.index.min() + 1
    main_frames = years_count * FRAMES_PER_YEAR
    intro_frames = int(round(INTRO_SECONDS * FPS))
    outro_frames = int(round(OUTRO_SECONDS * FPS))
    total_frames = intro_frames + main_frames + outro_frames
    duration_seconds = total_frames / FPS

    colors = make_color_map(data.columns.tolist())

    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
    fig.patch.set_facecolor("#0b111b")
    plt.subplots_adjust(left=0.21, right=0.96, top=0.90, bottom=0.08)

    with imageio.get_writer(OUT_VIDEO_SILENT, fps=FPS, codec="libx264", quality=8) as writer:
        for frame in range(total_frames):
            ax.clear()

            if frame < intro_frames:
                draw_year_frame(ax, data, colors, 0)
                draw_intro(ax, float(data.max().max()))
            elif frame >= intro_frames + main_frames:
                draw_year_frame(ax, data, colors, main_frames - 1)
                draw_outro(ax, float(data.max().max()))
            else:
                draw_year_frame(ax, data, colors, frame - intro_frames)

            fig.canvas.draw()
            frame_rgba = np.asarray(fig.canvas.buffer_rgba())
            frame_rgb = frame_rgba[:, :, :3]
            writer.append_data(frame_rgb)

    plt.close(fig)
    return duration_seconds


def synthesize_soundtrack(duration_s: float, sample_rate: int = 44100) -> None:
    n = int(sample_rate * duration_s)
    if n <= 0:
        raise ValueError("Duration must be positive")

    t = np.arange(n, dtype=np.float64) / sample_rate

    # History-like harmonic bed: evolving minor-ish progression.
    chord_roots = np.array([110.0, 98.0, 87.31, 82.41])  # A2, G2, F2, E2
    chord_third_ratio = np.array([1.20, 1.20, 1.20, 1.26])
    chord_len = 4.0

    chord_idx = ((t // chord_len).astype(int)) % len(chord_roots)
    roots = chord_roots[chord_idx]
    thirds = roots * chord_third_ratio[chord_idx]
    fifths = roots * 1.5

    def osc(freq_track: np.ndarray) -> np.ndarray:
        phase = 2 * np.pi * np.cumsum(freq_track) / sample_rate
        return np.sin(phase)

    pad = 0.34 * osc(roots) + 0.22 * osc(thirds) + 0.15 * osc(fifths)
    shimmer = 0.05 * osc(roots * 4.0)

    # Urgent but musical pulse via smoothed beat impulses.
    impulses = np.zeros(n, dtype=np.float64)
    beat_time = 0.0
    beat_index = 0
    while beat_time < duration_s:
        idx = int(round(beat_time * sample_rate))
        if idx < n:
            impulses[idx] += 1.0 if beat_index % 4 == 0 else 0.65
            ghost = idx + int(0.18 * sample_rate)
            if ghost < n:
                impulses[ghost] += 0.25

        bpm = 74.0 + 26.0 * (beat_time / max(duration_s, 1e-6))
        beat_time += 60.0 / bpm
        beat_index += 1

    k_t = np.arange(int(0.32 * sample_rate), dtype=np.float64) / sample_rate
    pulse_kernel = (1 - np.exp(-k_t * 70.0)) * np.exp(-k_t * 9.5)
    pulse_env = np.convolve(impulses, pulse_kernel, mode="full")[:n]

    growth = np.clip((t / max(duration_s, 1e-6)) ** 1.2, 0.0, 1.0)
    pulse_tone = np.sin(2 * np.pi * (52.0 + 8.0 * growth) * t)
    pulse = pulse_env * pulse_tone

    # Blend calm->urgent over time without harsh high-frequency noise.
    ambient_env = 0.58 - 0.22 * growth
    urgent_env = 0.14 + 0.52 * growth
    track = ambient_env * (pad + shimmer) + urgent_env * pulse

    # Final polish.
    fade = int(sample_rate * 1.0)
    if fade > 0 and len(track) > 2 * fade:
        track[:fade] *= np.linspace(0.0, 1.0, fade)
        track[-fade:] *= np.linspace(1.0, 0.0, fade)

    peak = np.max(np.abs(track))
    if peak > 1e-9:
        track = 0.92 * track / peak

    wav = (track * 32767).astype(np.int16)
    wavfile.write(OUT_AUDIO, sample_rate, wav)


def mux_audio_video() -> None:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(OUT_VIDEO_SILENT),
        "-i",
        str(OUT_AUDIO),
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

    if OUT_VIDEO_SILENT.exists():
        reader = imageio.get_reader(OUT_VIDEO_SILENT)
        try:
            meta = reader.get_meta_data()
        finally:
            reader.close()

        duration = float(meta.get("duration") or 0.0)
        if duration <= 0:
            data = load_country_timeseries()
            duration = render_video(data)
    else:
        data = load_country_timeseries()
        duration = render_video(data)

    synthesize_soundtrack(duration)
    mux_audio_video()

    print(f"Created: {OUT_VIDEO_FINAL}")
    print(f"Silent video: {OUT_VIDEO_SILENT}")
    print(f"Soundtrack: {OUT_AUDIO}")


if __name__ == "__main__":
    main()
