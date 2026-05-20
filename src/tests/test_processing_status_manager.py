from unittest.mock import MagicMock, patch

import pytest

from app.models import ProcessingJob
from podcast_processor.processing_status_manager import ProcessingStatusManager


@pytest.fixture
def status_manager(mock_db_session, test_logger):
    return ProcessingStatusManager(mock_db_session, test_logger)


def test_generate_job_id(status_manager):
    """Test job ID generation."""
    job_id = status_manager.generate_job_id()
    assert isinstance(job_id, str)
    assert len(job_id) > 0


def test_create_job(status_manager, mock_writer_client, mock_db_session, app):
    """Test job creation via writer service."""
    with app.app_context():
        post_guid = "guid123"
        job_id = "job123"

        mock_db_session.get.return_value = ProcessingJob(id=job_id)

        job = status_manager.create_job(post_guid, job_id)

        assert job.id == job_id
        assert mock_writer_client.action.called
        assert mock_writer_client.action.call_args[0][0] == "create_job"


def test_update_job_status(status_manager, mock_writer_client, app):
    """Test updating job status via writer service."""
    with app.app_context():
        # Using ProcessingJob directly but mocking its interaction with the DB
        job = ProcessingJob(id="job123", post_guid="guid123", total_steps=4)

        with patch(
            "podcast_processor.processing_status_manager.object_session"
        ) as mock_obj_session:
            mock_obj_session.return_value = MagicMock()

            status_manager.update_job_status(
                job, "running", 1, "Transcribing", progress=25.0
            )

            assert mock_writer_client.action.called
            assert mock_writer_client.action.call_args[0][0] == "update_job_status"
            assert mock_writer_client.action.call_args[0][1]["status"] == "running"
            assert mock_writer_client.action.call_args[0][1]["progress"] == 25.0


def test_mark_cancelled(status_manager, mock_writer_client):
    """Test marking a job as cancelled."""
    status_manager.mark_cancelled("job123", "User request")

    assert mock_writer_client.action.called
    assert mock_writer_client.action.call_args[0][0] == "mark_cancelled"
    assert mock_writer_client.action.call_args[0][1]["reason"] == "User request"
