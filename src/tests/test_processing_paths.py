import os
from pathlib import Path

import pytest

from shared.processing_paths import (
    get_in_root,
    get_instance_dir,
    get_job_unprocessed_path,
    get_srv_root,
    paths_from_unprocessed_path,
)


def test_paths_from_unprocessed_path():
    """Test generation of processing paths from unprocessed audio path."""
    unprocessed = "/data/in/some_podcast/episode1.mp3"
    feed_title = "My Cool Podcast!"

    paths = paths_from_unprocessed_path(unprocessed, feed_title)

    # Sanitization: "My Cool Podcast!" -> "My_Cool_Podcast"
    # Note: re.sub(r"[^a-zA-Z0-9\s_.-]", "", "My Cool Podcast!") -> "My Cool Podcast"
    # Then stripped and rstripped "."
    # Then spaces to underscores: "My_Cool_Podcast"

    expected_srv = get_srv_root() / "My_Cool_Podcast" / "episode1.mp3"
    assert paths.post_processed_audio_path == expected_srv


def test_get_job_unprocessed_path():
    """Test generation of unique per-job unprocessed path."""
    post_guid = "uuid123"
    job_id = "job456"
    post_title = "Episode 1: The Beginning?"

    path = get_job_unprocessed_path(post_guid, job_id, post_title)

    # Sanitization: "Episode 1: The Beginning?" -> "Episode 1 The Beginning"
    # Then f"{sanitized_title}.mp3"
    expected = (
        get_in_root() / "jobs" / post_guid / job_id / "Episode 1 The Beginning.mp3"
    )
    assert path == expected


def test_get_instance_dir_override(monkeypatch):
    """Test that instance directory can be overridden via environment variable."""
    monkeypatch.setenv("PODLY_INSTANCE_DIR", "/tmp/podly_test")
    assert get_instance_dir() == Path("/tmp/podly_test")


def test_sanitization_edge_cases():
    """Test sanitization with various special characters."""
    feed_title = "Podcast... with / Slashes & Dots."
    unprocessed = "test.mp3"

    paths = paths_from_unprocessed_path(unprocessed, feed_title)

    # "Podcast... with / Slashes & Dots."
    # re.sub(r"[^a-zA-Z0-9\s_.-]", "", ...) -> "Podcast... with  Slashes  Dots."
    # rstrip(".") -> "Podcast... with  Slashes  Dots"
    # re.sub(r"\s+", "_", ...) -> "Podcast..._with_Slashes_Dots"

    assert "Podcast..._with_Slashes_Dots" in str(paths.post_processed_audio_path)
