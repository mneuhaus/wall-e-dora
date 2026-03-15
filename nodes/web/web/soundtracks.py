"""Helpers for indexing and profiling ignored soundtrack files.

The soundtrack directory is intentionally not tracked in git, but the runtime
still needs a stable way to discover files, normalize their names, and expose
lightweight dance metadata to the UI.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

try:
    from mutagen import File as MutagenFile
except Exception:  # pragma: no cover - optional runtime dependency
    MutagenFile = None


REPO_ROOT = Path(__file__).resolve().parents[3]
SOUNDTRACK_DIR = REPO_ROOT / "nodes" / "audio" / "soundtrack"
SOUNDTRACK_CACHE_PATH = REPO_ROOT / "out" / "cache" / "soundtrack_index.json"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
FALLBACK_DANCE_PROFILE = {
    "style": "pulse",
    "energy": 0.62,
    "bpm": 116,
    "recommended": False,
    "gif": "lets-dance.gif",
    "eyes": ["lets-dance.gif", "lets-go.gif", "iris-yellow2.gif"],
    "blurb": "A punchier default groove for soundtrack tracks without a custom profile.",
}

TRACK_PROFILE_OVERRIDES: dict[str, dict[str, Any]] = {
    "genxbeats-smooth-hiphop-20221221-191926": {
        "style": "hiphop",
        "energy": 0.62,
        "bpm": 92,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "realistic-orange.gif", "iris-yellow2.gif"],
        "blurb": "Low, confident swagger with nods, shoulder-like arm accents, and heavier groove timing.",
    },
    "put-on-your-sunday-clothes": {
        "style": "showtime",
        "energy": 0.92,
        "bpm": 136,
        "recommended": True,
        "gif": "lets-dance.gif",
        "eyes": ["lets-dance.gif", "lets-go.gif", "iris-yellow2.gif"],
        "blurb": "Big-band, theatrical dancing with spins, arm flourishes, and confident turns.",
    },
    "2815-a-d": {
        "style": "glide",
        "energy": 0.28,
        "bpm": 82,
        "recommended": False,
        "gif": "realistic-orange.gif",
        "eyes": ["realistic-orange.gif", "ghibli-landscape.gif", "lonely.gif"],
        "blurb": "Slow drifting ambience with very gentle motion and lots of breathing room.",
    },
    "wall-e": {
        "style": "curious",
        "energy": 0.48,
        "bpm": 96,
        "recommended": False,
        "gif": "realistic-orange.gif",
        "eyes": ["realistic-orange.gif", "ghibli-landscape.gif", "landscape-yellow.gif"],
        "blurb": "Curious little head turns and playful pivots, more character than dancing.",
    },
    "the-spaceship": {
        "style": "glide",
        "energy": 0.44,
        "bpm": 92,
        "recommended": False,
        "gif": "iris-yellow2.gif",
        "eyes": ["iris-yellow2.gif", "ghibli-landscape.gif", "realistic-orange.gif"],
        "blurb": "Smooth lateral drifting with soft track pulses and slow looking around.",
    },
    "eve": {
        "style": "glide",
        "energy": 0.52,
        "bpm": 102,
        "recommended": False,
        "gif": "emotion-love.gif",
        "eyes": ["emotion-love.gif", "iris-yellow2.gif", "realistic-orange.gif"],
        "blurb": "Light, airy sways with a more graceful, admiring feel.",
    },
    "thrust": {
        "style": "pulse",
        "energy": 0.8,
        "bpm": 128,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "lets-dance.gif", "iris-yellow.gif"],
        "blurb": "Fast pulsing groove with strong alternating accents and sharper turns.",
    },
    "bubble-wrap": {
        "style": "bounce",
        "energy": 0.84,
        "bpm": 132,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "lets-dance.gif", "iris-yellow.gif"],
        "blurb": "Playful bouncy footwork with quick little hops, nods, and door pops.",
    },
    "la-vie-en-rose": {
        "style": "waltz",
        "energy": 0.38,
        "bpm": 84,
        "recommended": True,
        "gif": "emotion-love.gif",
        "eyes": ["emotion-love.gif", "longing.gif", "iris-yellow2.gif"],
        "blurb": "A slow romantic sway with softer turns and more tender eye contact.",
    },
    "first-date": {
        "style": "romance",
        "energy": 0.46,
        "bpm": 92,
        "recommended": True,
        "gif": "emotion-love.gif",
        "eyes": ["emotion-love.gif", "longing.gif", "realistic-orange.gif"],
        "blurb": "Shy, sweet dance gestures with careful pivots and softer arm poses.",
    },
    "72-degrees-and-sunny": {
        "style": "sway",
        "energy": 0.58,
        "bpm": 104,
        "recommended": True,
        "gif": "iris-yellow2.gif",
        "eyes": ["iris-yellow2.gif", "lets-go.gif", "realistic-orange.gif"],
        "blurb": "Easy-going groove with sunny side-to-side sways and cheerful head bobs.",
    },
    "define-dancing": {
        "style": "define-dancing",
        "energy": 0.76,
        "bpm": 108,
        "recommended": True,
        "gif": "lets-dance.gif",
        "eyes": ["lets-dance.gif", "emotion-love.gif", "iris-yellow2.gif"],
        "blurb": "The signature duet feel: flowing sways, gentle spins, and graceful call-and-response accents.",
    },
    "it-only-takes-a-moment": {
        "style": "romance",
        "energy": 0.4,
        "bpm": 80,
        "recommended": True,
        "gif": "longing.gif",
        "eyes": ["longing.gif", "emotion-love.gif", "lonely.gif"],
        "blurb": "Soft, sentimental motion with slower pacing and affectionate pauses.",
    },
    "down-to-earth": {
        "style": "showtime",
        "energy": 0.74,
        "bpm": 122,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "lets-dance.gif", "iris-yellow2.gif"],
        "blurb": "A bright finale groove with broader turns, lively arms, and crowd energy.",
    },
    "stayin-alive-show-cut": {
        "style": "disco",
        "energy": 0.82,
        "bpm": 104,
        "recommended": True,
        "gif": "lets-dance.gif",
        "eyes": ["lets-dance.gif", "iris-yellow2.gif", "lets-go.gif"],
        "blurb": "A confident disco strut with swaggering pivots, little arm pops, and crowd-pleasing timing.",
    },
    "ymca-show-cut": {
        "style": "showtime",
        "energy": 0.9,
        "bpm": 126,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "lets-dance.gif", "iris-yellow.gif"],
        "blurb": "A big singalong-style show cut with broad turns, happy accents, and easy crowd recognition.",
    },
    "ghostbusters-show-cut": {
        "style": "spooky-funk",
        "energy": 0.8,
        "bpm": 116,
        "recommended": True,
        "gif": "danger.gif",
        "eyes": ["danger.gif", "lets-go.gif", "iris-yellow.gif"],
        "blurb": "A playful spooky-funk groove with sneaky pivots, warning looks, and big crowd-recognition energy.",
    },
    "u-can-t-touch-this-show-cut": {
        "style": "robotic-funk",
        "energy": 0.88,
        "bpm": 134,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "iris-yellow.gif", "lets-dance.gif"],
        "blurb": "A punchy stop-and-go groove with robotic swagger, freezes, and cheeky little turns.",
    },
    "royaltyfreesongs-cosmic-drift-286316": {
        "style": "cosmic-glide",
        "energy": 0.56,
        "bpm": 96,
        "recommended": True,
        "gif": "ghibli-landscape.gif",
        "eyes": ["ghibli-landscape.gif", "iris-yellow2.gif", "realistic-orange.gif"],
        "blurb": "Slow orbital drifting with horizon scans, gentle sways, and bigger cinematic curves.",
    },
    "the-mountain-funk-groove-soul-317798": {
        "style": "soul-funk",
        "energy": 0.78,
        "bpm": 112,
        "recommended": True,
        "gif": "lets-dance.gif",
        "eyes": ["lets-dance.gif", "lets-go.gif", "iris-yellow2.gif"],
        "blurb": "Warm funk grooves with body sways, responsive arm phrasing, and playful track swagger.",
    },
    "the-mountain-uplifting-edm-145196": {
        "style": "festival-edm",
        "energy": 0.88,
        "bpm": 124,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "lets-dance.gif", "iris-yellow.gif"],
        "blurb": "Festival-sized rises and drops with stronger turns, big hands-up moments, and crowd energy.",
    },
    "thisisbeatkitchen-astral-120-bpm-instrumental-233206": {
        "style": "festival-edm",
        "energy": 0.86,
        "bpm": 120,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "lets-dance.gif", "iris-yellow2.gif"],
        "blurb": "A brighter electronic lift with cleaner pulses, more lift on the beat, and sharper drops.",
    },
    "thisisbeatkitchen-summer-110-bpm-dancehall-instrumental-233181": {
        "style": "dancehall-groove",
        "energy": 0.78,
        "bpm": 110,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "iris-yellow2.gif", "realistic-orange.gif"],
        "blurb": "Relaxed but buoyant dancehall bounce with rolling shoulders, cheeky peeks, and warm groove.",
    },
    "tim-kulig-free-music-sonic-sanctuary-144421": {
        "style": "ambient-glide",
        "energy": 0.44,
        "bpm": 94,
        "recommended": False,
        "gif": "ghibli-landscape.gif",
        "eyes": ["ghibli-landscape.gif", "realistic-orange.gif", "iris-yellow2.gif"],
        "blurb": "Ambient floating with broad arcs, quiet curiosity, and slower breathing room between accents.",
    },
    "zience88-tubevid-music-174132": {
        "style": "festival-edm",
        "energy": 0.82,
        "bpm": 122,
        "recommended": True,
        "gif": "lets-go.gif",
        "eyes": ["lets-go.gif", "lets-dance.gif", "iris-yellow.gif"],
        "blurb": "A compact festival-style burst with quick ramps, bold pivots, and big finish energy.",
    },
}

TITLE_SLUG_SUFFIXES = (
    "-from-wall-e-score",
    "-from-wall-e",
    "-single-version",
)

KEYWORD_PROFILE_HINTS = (
    (("dance", "waltz", "rose", "moment", "love", "date"), "waltz"),
    (("march", "mutiny", "directive", "axiom"), "march"),
    (("repair", "bubble", "gopher"), "bounce"),
    (("hiphop", "hip-hop", "boom-bap", "trap", "lofi"), "hiphop"),
    (("dancehall", "reggae", "summer"), "dancehall-groove"),
    (("edm", "festival", "electro", "house", "astral"), "festival-edm"),
    (("funk", "soul", "groove", "disco"), "soul-funk"),
    (("cosmic", "astral", "orbit", "sanctuary", "ambient"), "cosmic-glide"),
    (("static", "typing", "bnl", "m-o"), "robotic"),
    (("eve", "spaceship", "holo", "horizon"), "glide"),
    (("hyperjump", "thrust", "rogue", "adventure"), "pulse"),
)


_cached_signature: tuple | None = None
_cached_tracks: list[dict[str, Any]] | None = None


def slugify(value: str) -> str:
    """Return a stable, lowercase slug for filenames and IDs."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_value = ascii_value.replace("&", " and ")
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value)
    return ascii_value.strip("-") or "track"


def humanize_stem(stem: str) -> str:
    """Turn a compact file stem back into a nicer UI title."""
    cleaned = stem.replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title() or "Unknown Track"


def parse_track_number(raw_value: Any, stem: str) -> int:
    """Extract the best-effort track number from tags or the filename."""
    if raw_value:
        if isinstance(raw_value, list):
            raw_value = raw_value[0]
        match = re.search(r"\d+", str(raw_value))
        if match:
            return int(match.group(0))

    match = re.match(r"^\D*(\d{1,2})\b", stem)
    if match:
        return int(match.group(1))

    return 0


def read_tag(tags: Any, *keys: str) -> str:
    """Read a string-ish audio tag value from a mutagen tag mapping."""
    if not tags:
        return ""

    for key in keys:
        value = None
        try:
            value = tags.get(key)
        except Exception:
            value = None
        if value is None:
            continue
        if isinstance(value, list):
            value = value[0] if value else ""
        text = str(value).strip()
        if text:
            return text
    return ""


def md5_for_file(path: Path) -> str:
    """Calculate a stable MD5 hash for a soundtrack file."""
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def format_duration(duration_ms: int | None) -> str:
    """Return a compact mm:ss label."""
    if not duration_ms:
        return "?:??"

    total_seconds = max(0, int(round(duration_ms / 1000)))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def soundtrack_directory_signature() -> tuple:
    """Build a quick signature to skip unnecessary rescans."""
    SOUNDTRACK_DIR.mkdir(parents=True, exist_ok=True)
    signature = []
    for path in sorted(SOUNDTRACK_DIR.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file():
            stat = path.stat()
            signature.append((path.name, stat.st_mtime_ns, stat.st_size))
    return tuple(signature)


def read_cache() -> dict[str, dict[str, Any]]:
    """Load the soundtrack cache keyed by MD5 hash."""
    if not SOUNDTRACK_CACHE_PATH.exists():
        return {}

    try:
        payload = json.loads(SOUNDTRACK_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as error:
        logging.warning("Failed to read soundtrack cache: %s", error)
        return {}

    entries = payload.get("tracks") or []
    return {
        entry["hash"]: entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("hash")
    }


def write_cache(entries: list[dict[str, Any]]) -> None:
    """Persist the soundtrack cache for quick warm starts."""
    SOUNDTRACK_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOUNDTRACK_CACHE_PATH.write_text(
        json.dumps({"tracks": entries}, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def infer_style_from_title(title_slug: str) -> str:
    """Guess a dance style for tracks without an explicit override."""
    for keywords, style in KEYWORD_PROFILE_HINTS:
        if any(keyword in title_slug for keyword in keywords):
            return style
    return FALLBACK_DANCE_PROFILE["style"]


def canonicalize_title_slug(title_slug: str) -> str:
    """Strip soundtrack-specific suffixes so overrides still match tagged titles."""
    canonical = title_slug
    for suffix in TITLE_SLUG_SUFFIXES:
        if canonical.endswith(suffix):
            canonical = canonical[: -len(suffix)]
            break
    return canonical or title_slug


def infer_dance_profile(title: str, title_slug: str, track_number: int, duration_ms: int | None) -> dict[str, Any]:
    """Return a compact profile the frontend can turn into dance moves."""
    canonical_slug = canonicalize_title_slug(title_slug)
    preset = TRACK_PROFILE_OVERRIDES.get(canonical_slug) or TRACK_PROFILE_OVERRIDES.get(title_slug)
    bpm_hint_match = re.search(r"(?<!\d)(\d{2,3})[\s_-]*bpm(?!\d)", canonical_slug)
    bpm_hint = int(bpm_hint_match.group(1)) if bpm_hint_match else None
    if preset is None and (
        "imperial-march" in canonical_slug
        or "imperial-march" in title_slug
        or "darth-vader" in canonical_slug
    ):
        preset = {
            "style": "imperial-march",
            "energy": 0.78,
            "bpm": 104,
            "recommended": True,
            "gif": "danger.gif",
            "eyes": ["danger.gif", "iris-yellow.gif", "lets-go.gif"],
            "blurb": "Deliberate power-marching with stern pivots, heavy pauses, and villain energy.",
        }
    if preset is None:
        style = infer_style_from_title(canonical_slug)
        energy = FALLBACK_DANCE_PROFILE["energy"]
        bpm = FALLBACK_DANCE_PROFILE["bpm"]
        recommended = False
        gif = FALLBACK_DANCE_PROFILE["gif"]
        eyes = list(FALLBACK_DANCE_PROFILE["eyes"])
        blurb = FALLBACK_DANCE_PROFILE["blurb"]

        if style == "waltz":
            energy, bpm, gif, eyes = 0.42, 86, "emotion-love.gif", ["emotion-love.gif", "longing.gif", "iris-yellow2.gif"]
            blurb = "A slower, smoother dance with wider sways and softer emphasis."
        elif style == "hiphop":
            energy, bpm, gif, eyes = 0.62, 92, "lets-go.gif", ["lets-go.gif", "realistic-orange.gif", "iris-yellow2.gif"]
            blurb = "A lower, swaggering groove with nods, off-beat attitude, and more grounded timing."
        elif style == "dancehall-groove":
            energy, bpm, gif, eyes = 0.78, 110, "lets-go.gif", ["lets-go.gif", "iris-yellow2.gif", "realistic-orange.gif"]
            blurb = "Warm dancehall bounce with buoyant pulses, playful peeks, and rolling momentum."
        elif style == "festival-edm":
            energy, bpm, gif, eyes = 0.86, 122, "lets-go.gif", ["lets-go.gif", "lets-dance.gif", "iris-yellow.gif"]
            blurb = "Big electronic rises and drops with stronger chorus moments and more dramatic turns."
        elif style == "soul-funk":
            energy, bpm, gif, eyes = 0.78, 112, "lets-dance.gif", ["lets-dance.gif", "lets-go.gif", "iris-yellow2.gif"]
            blurb = "Loose funk swagger with body sways, mirrored arm phrases, and expressive track curves."
        elif style == "cosmic-glide":
            energy, bpm, gif, eyes = 0.56, 96, "ghibli-landscape.gif", ["ghibli-landscape.gif", "iris-yellow2.gif", "realistic-orange.gif"]
            blurb = "A wider floating glide with horizon scans, gentle orbits, and cinematic pacing."
        elif style == "ambient-glide":
            energy, bpm, gif, eyes = 0.42, 92, "ghibli-landscape.gif", ["ghibli-landscape.gif", "realistic-orange.gif", "iris-yellow2.gif"]
            blurb = "Very smooth, airy movement that favors character and breathing room over big dance hits."
        elif style == "march":
            energy, bpm, gif, eyes = 0.72, 118, "lets-go.gif", ["lets-go.gif", "iris-yellow.gif", "danger.gif"]
            blurb = "Steadier, more deliberate marching accents with stronger turns."
        elif style == "robotic":
            energy, bpm, gif, eyes = 0.6, 112, "iris-yellow.gif", ["iris-yellow.gif", "danger.gif", "realistic-orange.gif"]
            blurb = "Mechanical, syncopated pulses with cleaner stops and sharper pivots."
        elif style == "glide":
            energy, bpm, gif, eyes = 0.46, 94, "iris-yellow2.gif", ["iris-yellow2.gif", "realistic-orange.gif", "ghibli-landscape.gif"]
            blurb = "Smooth drifting movement with long curves and gentle steering."
        elif style == "curious":
            energy, bpm, gif, eyes = 0.5, 98, "realistic-orange.gif", ["realistic-orange.gif", "ghibli-landscape.gif", "landscape-yellow.gif"]
            blurb = "Less dance floor, more playful exploring with musical timing."
        elif style == "bounce":
            energy, bpm, gif, eyes = 0.82, 130, "lets-go.gif", ["lets-go.gif", "lets-dance.gif", "iris-yellow.gif"]
            blurb = "Playful bounces and little hops with quick head and arm accents."

        preset = {
            "style": style,
            "energy": energy,
            "bpm": bpm_hint or bpm,
            "recommended": recommended,
            "gif": gif,
            "eyes": eyes,
            "blurb": blurb,
        }

    profile = {**FALLBACK_DANCE_PROFILE, **preset}
    profile["style_label"] = {
        "define-dancing": "Define Dancing",
        "disco": "Disco",
        "showtime": "Showtime",
        "glide": "Glide",
        "waltz": "Waltz",
        "romance": "Romance",
        "pulse": "Pulse",
        "bounce": "Bounce",
        "hiphop": "Hip-Hop",
        "dancehall-groove": "Dancehall",
        "festival-edm": "Festival EDM",
        "soul-funk": "Soul Funk",
        "cosmic-glide": "Cosmic Glide",
        "ambient-glide": "Ambient Glide",
        "spooky-funk": "Spooky Funk",
        "robotic-funk": "Robotic Funk",
        "imperial-march": "Imperial March",
        "march": "March",
        "robotic": "Robotic",
        "curious": "Curious",
        "sway": "Sway",
    }.get(profile["style"], profile["style"].title())
    profile["title_slug"] = title_slug
    profile["canonical_title_slug"] = canonical_slug
    profile["track_number"] = track_number
    if duration_ms and duration_ms > 320000 and profile["style"] in {"showtime", "pulse"}:
        profile["recommended"] = True
    return profile


def read_audio_metadata(path: Path) -> dict[str, Any]:
    """Read title/artist/duration using mutagen when available."""
    title = humanize_stem(re.sub(r"^\d{2}-", "", path.stem))
    artist = ""
    album = ""
    track_number = parse_track_number(None, path.stem)
    duration_ms = 0

    if MutagenFile is None:
        return {
            "title": title,
            "artist": artist,
            "album": album,
            "track_number": track_number,
            "duration_ms": duration_ms,
        }

    try:
        audio = MutagenFile(str(path), easy=True)
    except Exception as error:
        logging.warning("Could not inspect soundtrack %s: %s", path.name, error)
        audio = None

    if audio is not None:
        title = read_tag(getattr(audio, "tags", None), "title") or title
        artist = read_tag(getattr(audio, "tags", None), "artist")
        album = read_tag(getattr(audio, "tags", None), "album")
        track_number = parse_track_number(read_tag(getattr(audio, "tags", None), "tracknumber"), path.stem)
        duration_ms = int(round(float(getattr(getattr(audio, "info", None), "length", 0.0) or 0.0) * 1000))

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "track_number": track_number,
        "duration_ms": duration_ms,
    }


def compact_filename(path: Path, metadata: dict[str, Any]) -> str:
    """Create a shorter on-disk soundtrack filename from tags or the original stem."""
    track_number = int(metadata.get("track_number") or 0)
    title = str(metadata.get("title") or humanize_stem(path.stem))
    title_slug = slugify(title)
    prefix = f"{track_number:02d}-" if track_number > 0 else ""
    return f"{prefix}{title_slug}{path.suffix.lower()}"


def normalize_soundtrack_directory() -> list[Path]:
    """Delete cruft files and rename tracks into short, stable filenames."""
    SOUNDTRACK_DIR.mkdir(parents=True, exist_ok=True)
    normalized_paths: list[Path] = []

    raw_files = sorted(SOUNDTRACK_DIR.iterdir(), key=lambda item: item.name.lower())
    for path in raw_files:
        if path.name == ".DS_Store":
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue

        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue

        metadata = read_audio_metadata(path)
        target_name = compact_filename(path, metadata)
        target_path = path.with_name(target_name)
        candidate_index = 2
        while target_path.exists() and target_path != path:
            target_path = path.with_name(f"{target_path.stem}-{candidate_index}{target_path.suffix}")
            candidate_index += 1

        if target_path != path:
            logging.info("Renaming soundtrack %s -> %s", path.name, target_path.name)
            path.rename(target_path)
            path = target_path

        normalized_paths.append(path)

    return sorted(normalized_paths, key=lambda item: item.name.lower())


def build_soundtrack_entry(path: Path, cached_entry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert a soundtrack file into the API/UI data shape."""
    file_hash = md5_for_file(path)
    if cached_entry and cached_entry.get("hash") == file_hash:
        metadata = {
            "title": cached_entry.get("title") or humanize_stem(path.stem),
            "artist": cached_entry.get("artist") or "",
            "album": cached_entry.get("album") or "",
            "track_number": int(cached_entry.get("track_number") or 0),
            "duration_ms": int(cached_entry.get("duration_ms") or 0),
        }
    else:
        metadata = read_audio_metadata(path)

    title_slug = slugify(metadata["title"])
    profile = infer_dance_profile(
        metadata["title"],
        title_slug,
        metadata["track_number"],
        metadata["duration_ms"],
    )
    track_id_prefix = f"{metadata['track_number']:02d}-" if metadata["track_number"] else ""
    track_id = f"{track_id_prefix}{title_slug}"

    return {
        "id": track_id,
        "filename": path.name,
        "title": metadata["title"],
        "artist": metadata["artist"],
        "album": metadata["album"],
        "track_number": metadata["track_number"],
        "duration_ms": metadata["duration_ms"],
        "duration_label": format_duration(metadata["duration_ms"]),
        "hash": file_hash,
        **profile,
    }


def load_soundtrack_index(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    """Return the normalized soundtrack index, refreshing the cache if needed."""
    global _cached_signature, _cached_tracks

    signature = soundtrack_directory_signature()
    if not force_refresh and signature == _cached_signature and _cached_tracks is not None:
        return list(_cached_tracks)

    cached_by_hash = {} if force_refresh else read_cache()
    normalized_paths = normalize_soundtrack_directory()

    entries = []
    for path in normalized_paths:
        cached_entry = None
        try:
            cached_entry = cached_by_hash.get(md5_for_file(path))
        except Exception:
            cached_entry = None
        entries.append(build_soundtrack_entry(path, cached_entry=cached_entry))

    entries.sort(key=lambda entry: (int(entry.get("track_number") or 0), entry.get("title", "").lower()))
    write_cache(entries)

    _cached_signature = soundtrack_directory_signature()
    _cached_tracks = entries
    return list(entries)
