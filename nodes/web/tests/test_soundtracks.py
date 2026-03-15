"""Tests for soundtrack indexing helpers."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))

from web import soundtracks  # noqa: E402


def test_normalize_soundtrack_directory_renames_files_and_removes_ds_store(tmp_path, monkeypatch):
    """Soundtracks should get short stable names and Finder cruft should disappear."""
    soundtrack_dir = tmp_path / "soundtrack"
    soundtrack_dir.mkdir()
    original = soundtrack_dir / "Various Artists - 22. Define Dancing (From _WALL-E__Score).mp3"
    original.write_bytes(b"demo-audio")
    (soundtrack_dir / ".DS_Store").write_bytes(b"junk")

    monkeypatch.setattr(soundtracks, "SOUNDTRACK_DIR", soundtrack_dir)
    monkeypatch.setattr(
        soundtracks,
        "read_audio_metadata",
        lambda path: {
            "title": "Define Dancing",
            "artist": "Various Artists",
            "album": "WALL-E",
            "track_number": 22,
            "duration_ms": 167000,
        },
    )

    normalized = soundtracks.normalize_soundtrack_directory()

    assert [path.name for path in normalized] == ["22-define-dancing.mp3"]
    assert not (soundtrack_dir / ".DS_Store").exists()


def test_load_soundtrack_index_applies_profiles(tmp_path, monkeypatch):
    """Indexed soundtrack entries should expose normalized dance metadata."""
    soundtrack_dir = tmp_path / "soundtrack"
    cache_path = tmp_path / "cache" / "soundtrack_index.json"
    soundtrack_dir.mkdir()
    track_path = soundtrack_dir / "01-put-on-your-sunday-clothes.mp3"
    track_path.write_bytes(b"track-data")

    monkeypatch.setattr(soundtracks, "SOUNDTRACK_DIR", soundtrack_dir)
    monkeypatch.setattr(soundtracks, "SOUNDTRACK_CACHE_PATH", cache_path)
    monkeypatch.setattr(
        soundtracks,
        "read_audio_metadata",
        lambda path: {
            "title": "Put On Your Sunday Clothes",
            "artist": "Various Artists",
            "album": "WALL-E",
            "track_number": 1,
            "duration_ms": 331559,
        },
    )

    tracks = soundtracks.load_soundtrack_index(force_refresh=True)

    assert len(tracks) == 1
    assert tracks[0]["filename"] == "01-put-on-your-sunday-clothes.mp3"
    assert tracks[0]["style"] == "showtime"
    assert tracks[0]["recommended"] is True
    assert tracks[0]["duration_label"] == "5:32"


def test_load_soundtrack_index_matches_define_dancing_override_with_score_suffix(tmp_path, monkeypatch):
    """Tagged score titles should still resolve to the intended special dance profile."""
    soundtrack_dir = tmp_path / "soundtrack"
    cache_path = tmp_path / "cache" / "soundtrack_index.json"
    soundtrack_dir.mkdir()
    track_path = soundtrack_dir / "22-define-dancing-from-wall-e-score.mp3"
    track_path.write_bytes(b"track-data")

    monkeypatch.setattr(soundtracks, "SOUNDTRACK_DIR", soundtrack_dir)
    monkeypatch.setattr(soundtracks, "SOUNDTRACK_CACHE_PATH", cache_path)
    monkeypatch.setattr(
        soundtracks,
        "read_audio_metadata",
        lambda path: {
            "title": 'Define Dancing (From "WALL-E"/Score)',
            "artist": "Thomas Newman",
            "album": "WALL-E",
            "track_number": 22,
            "duration_ms": 143412,
        },
    )

    tracks = soundtracks.load_soundtrack_index(force_refresh=True)

    assert tracks[0]["style"] == "define-dancing"
    assert tracks[0]["canonical_title_slug"] == "define-dancing"


def test_load_soundtrack_index_applies_show_cut_overrides(tmp_path, monkeypatch):
    """Custom short show cuts should expose their intended dance profiles."""
    soundtrack_dir = tmp_path / "soundtrack"
    cache_path = tmp_path / "cache" / "soundtrack_index.json"
    soundtrack_dir.mkdir()
    stayin_path = soundtrack_dir / "30-stayin-alive-show-cut.mp3"
    ymca_path = soundtrack_dir / "31-ymca-show-cut.mp3"
    stayin_path.write_bytes(b"track-a")
    ymca_path.write_bytes(b"track-b")

    monkeypatch.setattr(soundtracks, "SOUNDTRACK_DIR", soundtrack_dir)
    monkeypatch.setattr(soundtracks, "SOUNDTRACK_CACHE_PATH", cache_path)

    def fake_metadata(path):
        if path.name == "30-stayin-alive-show-cut.mp3":
            return {
                "title": "Stayin' Alive Show Cut",
                "artist": "Bee Gees",
                "album": "WALL-E Dance Cuts",
                "track_number": 30,
                "duration_ms": 39000,
            }
        return {
            "title": "YMCA Show Cut",
            "artist": "Village People",
            "album": "WALL-E Dance Cuts",
            "track_number": 31,
            "duration_ms": 38000,
        }

    monkeypatch.setattr(soundtracks, "read_audio_metadata", fake_metadata)

    tracks = soundtracks.load_soundtrack_index(force_refresh=True)

    assert [track["id"] for track in tracks] == ["30-stayin-alive-show-cut", "31-ymca-show-cut"]
    assert tracks[0]["style"] == "disco"
    assert tracks[0]["style_label"] == "Disco"
    assert tracks[1]["style"] == "showtime"
    assert tracks[1]["recommended"] is True


def test_load_soundtrack_index_applies_fun_show_cut_profiles(tmp_path, monkeypatch):
    """Additional fun show cuts should get explicit UI-facing styles."""
    soundtrack_dir = tmp_path / "soundtrack"
    cache_path = tmp_path / "cache" / "soundtrack_index.json"
    soundtrack_dir.mkdir()
    ghostbusters_path = soundtrack_dir / "32-ghostbusters-show-cut.mp3"
    cant_touch_path = soundtrack_dir / "33-u-cant-touch-this-show-cut.mp3"
    ghostbusters_path.write_bytes(b"track-c")
    cant_touch_path.write_bytes(b"track-d")

    monkeypatch.setattr(soundtracks, "SOUNDTRACK_DIR", soundtrack_dir)
    monkeypatch.setattr(soundtracks, "SOUNDTRACK_CACHE_PATH", cache_path)

    def fake_metadata(path):
        if path.name == "32-ghostbusters-show-cut.mp3":
            return {
                "title": "Ghostbusters Show Cut",
                "artist": "Ray Parker Jr.",
                "album": "WALL-E Dance Cuts",
                "track_number": 32,
                "duration_ms": 39000,
            }
        return {
            "title": "U Can't Touch This Show Cut",
            "artist": "M.C. Hammer",
            "album": "WALL-E Dance Cuts",
            "track_number": 33,
            "duration_ms": 37000,
        }

    monkeypatch.setattr(soundtracks, "read_audio_metadata", fake_metadata)

    tracks = soundtracks.load_soundtrack_index(force_refresh=True)

    assert [track["id"] for track in tracks] == [
        "32-ghostbusters-show-cut",
        "33-u-can-t-touch-this-show-cut",
    ]
    assert tracks[0]["style"] == "spooky-funk"
    assert tracks[0]["style_label"] == "Spooky Funk"
    assert tracks[1]["style"] == "robotic-funk"
    assert tracks[1]["style_label"] == "Robotic Funk"


def test_load_soundtrack_index_uses_specific_styles_for_current_cc_tracks(tmp_path, monkeypatch):
    """Current long-form soundtrack files should no longer all collapse to the generic pulse style."""
    soundtrack_dir = tmp_path / "soundtrack"
    cache_path = tmp_path / "cache" / "soundtrack_index.json"
    soundtrack_dir.mkdir()
    hiphop_path = soundtrack_dir / "genxbeats-smooth-hiphop-20221221-191926.mp3"
    dancehall_path = soundtrack_dir / "thisisbeatkitchen-summer-110-bpm-dancehall-instrumental-233181.mp3"
    ambient_path = soundtrack_dir / "tim-kulig-free-music-sonic-sanctuary-144421.mp3"
    for path in (hiphop_path, dancehall_path, ambient_path):
        path.write_bytes(b"track")

    monkeypatch.setattr(soundtracks, "SOUNDTRACK_DIR", soundtrack_dir)
    monkeypatch.setattr(soundtracks, "SOUNDTRACK_CACHE_PATH", cache_path)

    def fake_metadata(path):
        if path.name == hiphop_path.name:
            return {
                "title": "Genxbeats Smooth Hiphop 20221221 191926",
                "artist": "Genxbeats",
                "album": "",
                "track_number": 0,
                "duration_ms": 235990,
            }
        if path.name == dancehall_path.name:
            return {
                "title": "Thisisbeatkitchen Summer 110 Bpm Dancehall Instrumental 233181",
                "artist": "Thisisbeatkitchen",
                "album": "",
                "track_number": 0,
                "duration_ms": 165888,
            }
        return {
            "title": "Tim Kulig Free Music Sonic Sanctuary 144421",
            "artist": "Tim Kulig",
            "album": "",
            "track_number": 0,
            "duration_ms": 280084,
        }

    monkeypatch.setattr(soundtracks, "read_audio_metadata", fake_metadata)

    tracks = {track["filename"]: track for track in soundtracks.load_soundtrack_index(force_refresh=True)}

    assert tracks[hiphop_path.name]["style"] == "hiphop"
    assert tracks[hiphop_path.name]["style_label"] == "Hip-Hop"
    assert tracks[dancehall_path.name]["style"] == "dancehall-groove"
    assert tracks[dancehall_path.name]["bpm"] == 110
    assert tracks[ambient_path.name]["style"] == "ambient-glide"
