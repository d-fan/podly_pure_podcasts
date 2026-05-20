from unittest.mock import MagicMock

import pytest

from app.db_commit import safe_commit


def test_safe_commit_success():
    """Test safe_commit when session.commit succeeds."""
    mock_session = MagicMock()
    safe_commit(mock_session, context="test_success")
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()


def test_safe_commit_failure_and_rollback():
    """Test safe_commit when session.commit fails and rollback is triggered."""
    mock_session = MagicMock()
    mock_session.commit.side_effect = Exception("Commit failed")

    with pytest.raises(Exception, match="Commit failed"):
        safe_commit(mock_session, context="test_failure")

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_called_once()


def test_safe_commit_no_raise_on_failure():
    """Test safe_commit with must_succeed=False."""
    mock_session = MagicMock()
    mock_session.commit.side_effect = Exception("Commit failed")

    # Should not raise
    safe_commit(mock_session, context="test_no_raise", must_succeed=False)

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_called_once()


def test_safe_commit_rollback_failure():
    """Test safe_commit when both commit and rollback fail."""
    mock_session = MagicMock()
    mock_session.commit.side_effect = Exception("Commit failed")
    mock_session.rollback.side_effect = Exception("Rollback failed")

    with pytest.raises(Exception, match="Commit failed"):
        safe_commit(mock_session, context="test_double_failure")

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_called_once()
