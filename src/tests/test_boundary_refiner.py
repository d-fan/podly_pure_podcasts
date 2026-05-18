from unittest.mock import MagicMock, patch

import pytest

from podcast_processor.boundary_refiner import (
    MAX_END_EXTENSION_SECONDS,
    MAX_START_EXTENSION_SECONDS,
    BoundaryRefinement,
    BoundaryRefiner,
)


@pytest.fixture
def boundary_refiner(test_config):
    return BoundaryRefiner(test_config)


def test_heuristic_refine(boundary_refiner):
    """Test pattern-based heuristic refinement."""
    ad_start = 100.0
    ad_end = 120.0
    context = [
        {"start_time": 95.0, "text": "This episode is brought to you by our sponsor."},
        {"start_time": 105.0, "text": "Inside the ad."},
        {
            "start_time": 125.0,
            "text": "Visit our website at example.com for more info.",
        },
    ]

    refined = boundary_refiner._heuristic_refine(ad_start, ad_end, context)

    assert refined.refined_start == 95.0
    assert refined.refined_end == 125.0 + 5.0  # end_time fallback is start + 5
    assert refined.start_adjustment_reason == "heuristic"


def test_validate_constraints(boundary_refiner):
    """Test that refinement is constrained by maximum allowed expansion."""
    orig_start = 100.0
    orig_end = 200.0

    # Try to expand beyond MAX_START_EXTENSION_SECONDS (30s)
    refinement = BoundaryRefinement(
        refined_start=orig_start - 100.0,
        refined_end=orig_end + 100.0,
        start_adjustment_reason="too_much",
        end_adjustment_reason="too_much",
    )

    validated = boundary_refiner._validate(orig_start, orig_end, refinement)

    assert validated.refined_start == orig_start - MAX_START_EXTENSION_SECONDS
    assert validated.refined_end == orig_end + MAX_END_EXTENSION_SECONDS


def test_refine_llm_success(boundary_refiner, mock_writer_client):
    """Test successful LLM refinement."""
    with patch("litellm.completion") as mock_completion:
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"refined_start": 98.5, "refined_end": 122.0, "start_reason": "intro", "end_reason": "outro"}'
                )
            )
        ]
        mock_completion.return_value = mock_response
        mock_writer_client.action.return_value = MagicMock(
            success=True, data={"model_call_id": 123}
        )

        refined = boundary_refiner.refine(
            ad_start=100.0,
            ad_end=120.0,
            confidence=0.9,
            all_segments=[
                {"start_time": 90.0, "end_time": 95.0, "text": "Prev"},
                {"start_time": 98.0, "end_time": 102.0, "text": "Start"},
                {"start_time": 118.0, "end_time": 122.0, "text": "End"},
            ],
            post_id=1,
            first_seq_num=10,
            last_seq_num=20,
        )

        assert refined.refined_start == 98.5
        assert refined.refined_end == 122.0
        assert mock_writer_client.action.called  # upsert_model_call

        # Check if update was called with status="success"
        success_call = False
        for call in mock_writer_client.update.call_args_list:
            if call.args[2].get("status") == "success":
                success_call = True
                break
        assert success_call


def test_refine_llm_malformed_json_fallback(boundary_refiner, mock_writer_client):
    """Test fallback to heuristic when LLM returns malformed JSON."""
    with patch("litellm.completion") as mock_completion:
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="This is not JSON but it mentions sponsor.com"
                )
            )
        ]
        mock_completion.return_value = mock_response
        mock_writer_client.action.return_value = MagicMock(
            success=True, data={"model_call_id": 123}
        )

        # Should fallback to heuristic
        # Context will include segments
        refined = boundary_refiner.refine(
            ad_start=100.0,
            ad_end=120.0,
            confidence=0.9,
            all_segments=[
                {"start_time": 95.0, "text": "Brought to you by sponsor."},
                {"start_time": 105.0, "text": "Ad"},
                {"start_time": 125.0, "text": "Visit .com"},
            ],
            post_id=1,
            first_seq_num=10,
            last_seq_num=20,
        )

        assert refined.refined_start == 95.0
        assert refined.start_adjustment_reason == "heuristic"
        # Verify ModelCall was updated with success_heuristic status
        heuristic_call = False
        for call in mock_writer_client.update.call_args_list:
            if call.args[2].get("status") == "success_heuristic":
                heuristic_call = True
                break
        assert heuristic_call
