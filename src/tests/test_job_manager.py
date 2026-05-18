import os
from unittest.mock import MagicMock, patch

import pytest

from app.job_manager import JobManager


class MockPost:
    def __init__(
        self,
        guid="guid123",
        title="Test",
        whitelisted=True,
        download_url="http://x.mp3",
        processed_audio_path=None,
    ):
        self.guid = guid
        self.title = title
        self.whitelisted = whitelisted
        self.download_url = download_url
        self.processed_audio_path = processed_audio_path


@pytest.fixture
def mock_status_manager():
    manager = MagicMock()
    manager.generate_job_id.return_value = "job123"
    manager.create_job.return_value = MagicMock(id="job123", status="pending")
    return manager


@pytest.fixture
def job_manager(mock_status_manager, test_logger):
    return JobManager(
        post_guid="guid123",
        status_manager=mock_status_manager,
        logger_obj=test_logger,
        run_id="run123",
    )


def test_ensure_job_creates_new(job_manager, mock_status_manager, app):
    """Test that ensure_job creates a new job if none exists."""
    with app.app_context():
        with patch("app.models.ProcessingJob.query") as mock_query:
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = (
                None
            )

            job = job_manager.ensure_job()

            assert job.id == "job123"
            assert mock_status_manager.create_job.called


def test_load_and_validate_post_missing(job_manager, app):
    """Test validation when post is missing."""
    with app.app_context():
        with patch("app.models.Post.query") as mock_query:
            mock_query.filter_by.return_value.first.return_value = None

            post, error = job_manager._load_and_validate_post()

            assert post is None
            assert error["error_code"] == "NOT_FOUND"


def test_load_and_validate_post_not_whitelisted(job_manager, app):
    """Test validation when post is not whitelisted."""
    with app.app_context():
        with patch("app.models.Post.query") as mock_query:
            mock_query.filter_by.return_value.first.return_value = MockPost(
                whitelisted=False
            )

            post, error = job_manager._load_and_validate_post()

            assert post is None
            assert error["error_code"] == "NOT_WHITELISTED"


def test_load_and_validate_post_already_processed(job_manager, tmp_path, app):
    """Test validation when post is already processed."""
    processed_file = tmp_path / "processed.mp3"
    processed_file.write_text("audio")

    with app.app_context():
        with patch("app.models.Post.query") as mock_query:
            mock_query.filter_by.return_value.first.return_value = MockPost(
                processed_audio_path=str(processed_file)
            )

            post, error = job_manager._load_and_validate_post()

            assert post is None
            assert error["status"] == "skipped"
