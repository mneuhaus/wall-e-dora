"""Local soundtrack structure analysis for on-robot dance choreography.

The dance runtime should stay on WALL-E itself. To make the choreography feel
more musical without streaming control decisions from the browser, this module
extracts a small amount of structure from local soundtrack files and caches the
result by MD5 hash.
"""

from __future__ import annotations

from array import array
import hashlib
import json
import logging
import math
from pathlib import Path
import re
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SOUNDTRACK_DIR = REPO_ROOT / "nodes" / "audio" / "soundtrack"
ANALYSIS_CACHE_PATH = REPO_ROOT / "out" / "cache" / "soundtrack_analysis.json"
ANALYSIS_VERSION = 1
DECODE_SAMPLE_RATE = 11025
RMS_WINDOW_SECONDS = 0.36
RMS_HOP_SECONDS = 0.18


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = _clamp(ratio, 0.0, 1.0) * (len(ordered) - 1)
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _md5_for_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_cache() -> dict[str, dict[str, Any]]:
    if not ANALYSIS_CACHE_PATH.exists():
        return {}

    try:
        payload = json.loads(ANALYSIS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as error:
        logging.warning("Failed to read soundtrack analysis cache: %s", error)
        return {}

    entries = payload.get("entries") or []
    return {
        entry["hash"]: entry
        for entry in entries
        if isinstance(entry, dict)
        and entry.get("hash")
        and int(entry.get("version") or 0) == ANALYSIS_VERSION
    }


def _write_cache(entries: list[dict[str, Any]]) -> None:
    ANALYSIS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANALYSIS_CACHE_PATH.write_text(
        json.dumps({"version": ANALYSIS_VERSION, "entries": entries}, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _decode_audio(path: Path, sample_rate: int = DECODE_SAMPLE_RATE) -> array[float] | None:
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "pipe:1",
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        logging.warning("ffmpeg is not available; dance soundtrack analysis is disabled")
        return None
    except subprocess.CalledProcessError as error:
        logging.warning("ffmpeg could not decode %s: %s", path.name, error.stderr.decode("utf-8", "ignore"))
        return None

    samples = array("f")
    samples.frombytes(result.stdout)
    return samples


def _moving_average(values: list[float], radius: int = 1) -> list[float]:
    if not values or radius <= 0:
        return list(values)

    smoothed: list[float] = []
    for index in range(len(values)):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        smoothed.append(_mean(values[start:end]))
    return smoothed


def _build_envelope(samples: array[float], sample_rate: int) -> tuple[list[float], list[float]]:
    window_size = max(256, int(sample_rate * RMS_WINDOW_SECONDS))
    hop_size = max(128, int(sample_rate * RMS_HOP_SECONDS))
    if len(samples) < window_size:
        rms = math.sqrt(sum(sample * sample for sample in samples) / max(1, len(samples)))
        return [0.0], [rms]

    times: list[float] = []
    envelope: list[float] = []
    for start in range(0, len(samples) - window_size + 1, hop_size):
        window = samples[start:start + window_size]
        square_sum = sum(sample * sample for sample in window)
        envelope.append(math.sqrt(square_sum / window_size))
        times.append((start + (window_size / 2)) / sample_rate)

    return times, _moving_average(envelope, radius=1)


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    minimum = min(values)
    maximum = max(values)
    span = maximum - minimum
    if span <= 1e-9:
        return [0.5 for _ in values]
    return [(value - minimum) / span for value in values]


def _estimate_bpm(envelope: list[float], hop_seconds: float, fallback_bpm: float | None) -> float:
    if len(envelope) < 8:
        return float(fallback_bpm or 116.0)

    centered = [value - _mean(envelope) for value in envelope]
    if fallback_bpm and fallback_bpm > 0:
        minimum_bpm = max(72, int(round(fallback_bpm - 16)))
        maximum_bpm = min(168, int(round(fallback_bpm + 16)))
    else:
        minimum_bpm = 76
        maximum_bpm = 152

    best_bpm = float(fallback_bpm or 116.0)
    best_score = float("-inf")

    for bpm in range(minimum_bpm, maximum_bpm + 1):
        beat_lag = int(round((60.0 / bpm) / hop_seconds))
        if beat_lag <= 1 or beat_lag >= len(centered):
            continue

        primary = 0.0
        harmonic = 0.0
        for index in range(beat_lag, len(centered)):
            primary += centered[index] * centered[index - beat_lag]

        double_lag = beat_lag * 2
        if double_lag < len(centered):
            for index in range(double_lag, len(centered)):
                harmonic += centered[index] * centered[index - double_lag]

        fallback_bias = 0.0
        if fallback_bpm and fallback_bpm > 0:
            fallback_bias = max(0.0, 1.0 - (abs(fallback_bpm - bpm) / 18.0))

        score = primary + (harmonic * 0.35) + (fallback_bias * 2.2)
        if score > best_score:
            best_score = score
            best_bpm = float(bpm)

    if fallback_bpm and fallback_bpm > 0 and abs(best_bpm - fallback_bpm) > 8:
        return float(fallback_bpm)

    return _clamp(best_bpm, 72.0, 168.0)


def _detect_accent_times(times: list[float], envelope: list[float]) -> list[float]:
    if len(times) < 3 or len(envelope) < 3:
        return []

    threshold = max(0.58, _percentile(envelope, 0.72))
    accent_times: list[float] = []
    accent_values: list[float] = []
    min_spacing = 0.42

    for index in range(1, len(envelope) - 1):
        current = envelope[index]
        if current < threshold:
            continue
        if current < envelope[index - 1] or current < envelope[index + 1]:
            continue

        time_point = float(times[index])
        if accent_times and (time_point - accent_times[-1]) < min_spacing:
            if current > accent_values[-1]:
                accent_times[-1] = time_point
                accent_values[-1] = current
            continue

        accent_times.append(time_point)
        accent_values.append(current)

    return accent_times


def _build_sections(
    duration_seconds: float,
    times: list[float],
    envelope: list[float],
    accent_times: list[float],
    bpm: float,
) -> list[dict[str, Any]]:
    if duration_seconds <= 0:
        return []

    beat_seconds = 60.0 / max(72.0, bpm)
    section_duration = _clamp(beat_seconds * 16.0, 7.0, 13.5)
    accent_density_scale = max(0.4, 1.0 / section_duration)

    sections: list[dict[str, Any]] = []
    cursor = 0.0
    while cursor < duration_seconds:
        section_start = cursor
        section_end = min(duration_seconds, section_start + section_duration)
        section_values = [
            envelope[index]
            for index, time_point in enumerate(times)
            if section_start <= time_point < section_end
        ]
        if not section_values:
            section_values = [0.0]
        section_accents = [
            time_point
            for time_point in accent_times
            if section_start <= time_point < section_end
        ]
        sections.append({
            "start": round(section_start, 3),
            "end": round(section_end, 3),
            "duration": round(section_end - section_start, 3),
            "energy": round(_mean(section_values), 4),
            "peak_energy": round(max(section_values), 4),
            "accent_density": round(len(section_accents) * accent_density_scale, 4),
            "accent_count": len(section_accents),
        })
        cursor = section_end

    energies = [section["energy"] for section in sections]
    density_values = [section["accent_density"] for section in sections]
    q25 = _percentile(energies, 0.25)
    q50 = _percentile(energies, 0.5)
    q75 = _percentile(energies, 0.75)
    density_median = _percentile(density_values, 0.5)

    for index, section in enumerate(sections):
        previous_energy = energies[index - 1] if index > 0 else section["energy"]
        next_energy = energies[index + 1] if index < len(sections) - 1 else section["energy"]
        delta = round(next_energy - section["energy"], 4)
        role = "groove"

        if index == 0:
            role = "intro"
        elif index == len(sections) - 1:
            role = "finale"
        elif section["energy"] >= q75 and section["accent_density"] >= density_median:
            role = "peak"
        elif delta >= 0.08:
            role = "build"
        elif previous_energy - section["energy"] >= 0.12 and section["energy"] <= q50:
            role = "breakdown"
        elif section["energy"] <= q25:
            role = "breath"

        section["role"] = role
        section["trend"] = (
            "rising" if delta >= 0.05 else "falling" if delta <= -0.05 else "steady"
        )

    return sections


def _sanitize_analysis(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": ANALYSIS_VERSION,
        "hash": str(entry.get("hash") or ""),
        "filename": str(entry.get("filename") or ""),
        "duration_seconds": float(entry.get("duration_seconds") or 0.0),
        "estimated_bpm": float(entry.get("estimated_bpm") or 116.0),
        "accent_times": [
            round(float(time_point), 3)
            for time_point in (entry.get("accent_times") or [])
        ],
        "sections": [
            {
                "start": float(section.get("start") or 0.0),
                "end": float(section.get("end") or 0.0),
                "duration": float(section.get("duration") or 0.0),
                "energy": float(section.get("energy") or 0.0),
                "peak_energy": float(section.get("peak_energy") or 0.0),
                "accent_density": float(section.get("accent_density") or 0.0),
                "accent_count": int(section.get("accent_count") or 0),
                "role": str(section.get("role") or "groove"),
                "trend": str(section.get("trend") or "steady"),
            }
            for section in (entry.get("sections") or [])
            if isinstance(section, dict)
        ],
    }


def analyze_soundtrack_file(path: Path, *, fallback_bpm: float | None = None) -> dict[str, Any] | None:
    samples = _decode_audio(path)
    if samples is None or len(samples) == 0:
        return None

    times, envelope = _build_envelope(samples, DECODE_SAMPLE_RATE)
    normalized_envelope = _normalize(envelope)
    accent_times = _detect_accent_times(times, normalized_envelope)
    estimated_bpm = _estimate_bpm(normalized_envelope, RMS_HOP_SECONDS, fallback_bpm)
    duration_seconds = len(samples) / DECODE_SAMPLE_RATE
    sections = _build_sections(
        duration_seconds,
        times,
        normalized_envelope,
        accent_times,
        estimated_bpm,
    )

    return {
        "version": ANALYSIS_VERSION,
        "hash": _md5_for_file(path),
        "filename": path.name,
        "duration_seconds": round(duration_seconds, 3),
        "estimated_bpm": round(estimated_bpm, 2),
        "accent_times": [round(time_point, 3) for time_point in accent_times[:192]],
        "sections": sections,
    }


def load_soundtrack_analysis(
    filename: str,
    *,
    fallback_bpm: float | None = None,
    force_refresh: bool = False,
) -> dict[str, Any] | None:
    path = SOUNDTRACK_DIR / Path(filename).name
    if not path.exists() or not path.is_file():
        return None

    file_hash = _md5_for_file(path)
    cache_entries = {} if force_refresh else _read_cache()
    cached_entry = cache_entries.get(file_hash)
    if cached_entry is not None:
        return _sanitize_analysis(cached_entry)

    analysis = analyze_soundtrack_file(path, fallback_bpm=fallback_bpm)
    if analysis is None:
        return None

    cache_entries[file_hash] = analysis
    _write_cache(list(cache_entries.values()))
    return _sanitize_analysis(analysis)


def warm_soundtrack_analysis_cache() -> int:
    SOUNDTRACK_DIR.mkdir(parents=True, exist_ok=True)
    analyzed = 0
    for path in sorted(SOUNDTRACK_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".mp3", ".wav", ".ogg", ".aac", ".m4a", ".flac"}:
            continue
        if load_soundtrack_analysis(path.name) is not None:
            analyzed += 1
    return analyzed
