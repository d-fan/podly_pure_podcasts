import pytest

from app.models import Identification, TranscriptSegment
from podcast_processor.ad_merger import AdGroup, AdMerger


@pytest.fixture
def ad_merger():
    return AdMerger()


def test_group_by_proximity_basic(ad_merger):
    """Test basic grouping of segments by proximity."""
    segments = [
        TranscriptSegment(id=1, start_time=0.0, end_time=5.0, text="Ad 1"),
        TranscriptSegment(id=2, start_time=10.0, end_time=15.0, text="Ad 2"),
        TranscriptSegment(id=3, start_time=30.0, end_time=35.0, text="Ad 3"),
    ]
    identifications = [
        Identification(transcript_segment_id=1, confidence=0.9),
        Identification(transcript_segment_id=2, confidence=0.9),
        Identification(transcript_segment_id=3, confidence=0.9),
    ]

    groups = ad_merger._group_by_proximity(segments, identifications, max_gap=8.0)

    assert len(groups) == 2
    assert groups[0].start_time == 0.0
    assert groups[0].end_time == 15.0
    assert len(groups[0].segments) == 2
    assert groups[1].start_time == 30.0
    assert groups[1].end_time == 35.0
    assert len(groups[1].segments) == 1


def test_extract_keywords(ad_merger):
    """Test extraction of keywords from segments."""
    segments = [
        TranscriptSegment(
            text="Visit example.com to save 20% with promo code PODCAST."
        ),
        TranscriptSegment(
            text="Call us at 555-0199 or visit our brand site example.com."
        ),
        TranscriptSegment(text="BrandName BrandName is the best."),
    ]

    keywords = ad_merger._extract_keywords(segments)

    assert "example.com" in keywords
    assert any("save" in k for k in keywords)
    assert any("promo" in k for k in keywords)
    # Brand names (capitalized words appearing 2+ times)
    # "BrandName BrandName is the best."
    # AdMerger._extract_keywords uses: re.findall(r"\b[A-Z][a-z]+\b", " ".join(s.text for s in segments))
    # "BrandName" has "B" and "N" caps. [A-Z][a-z]+ will only match "Brand" and "Name".
    # Wait, "BrandName" will match NOTHING because it has 'N' in the middle.
    # [A-Z][a-z]+ matches a capital letter followed by one or more lowercase letters.
    # So "Brand" matches, "Name" matches.
    # Let's use simple capitalized words.
    segments_with_brand = [
        TranscriptSegment(text="Coca Cola Coca Cola is refreshing."),
        TranscriptSegment(text="Coca Cola is the best."),
    ]
    keywords_with_brand = ad_merger._extract_keywords(segments_with_brand)
    assert "coca" in keywords_with_brand
    assert "cola" in keywords_with_brand


def test_should_merge_shared_keywords(ad_merger):
    """Test merging groups based on shared keywords."""
    group1 = AdGroup(
        segments=[],
        identifications=[],
        start_time=0.0,
        end_time=30.0,
        confidence_avg=0.8,
        keywords=["sponsor.com", "offer"],
    )
    group2 = AdGroup(
        segments=[],
        identifications=[],
        start_time=40.0,
        end_time=70.0,
        confidence_avg=0.8,
        keywords=["sponsor.com", "save"],
    )

    assert ad_merger._should_merge(group1, group2) is True


def test_is_valid_group_filtering(ad_merger):
    """Test validation filtering for groups."""
    seg1 = TranscriptSegment(id=1, start_time=0.0, end_time=10.0, text="Ad 1")
    seg2 = TranscriptSegment(id=2, start_time=10.0, end_time=20.0, text="Ad 2")

    # Valid group: high confidence
    valid_group = AdGroup(
        segments=[seg1, seg2],
        identifications=[],
        start_time=0.0,
        end_time=20.0,
        confidence_avg=0.95,
        keywords=[],
    )
    assert ad_merger._is_valid_group(valid_group) is True

    # Invalid group: long duration, no keywords, low confidence
    invalid_group = AdGroup(
        segments=[seg1],
        identifications=[],
        start_time=0.0,
        end_time=200.0,
        confidence_avg=0.8,
        keywords=[],
    )
    assert ad_merger._is_valid_group(invalid_group) is False


def test_merge_full_flow(ad_merger):
    """Test the full merge flow."""
    segments = [
        TranscriptSegment(
            id=1, start_time=0.0, end_time=10.0, text="Sponsor A intro at sponsor.com"
        ),
        TranscriptSegment(
            id=2, start_time=15.0, end_time=25.0, text="Sponsor A details"
        ),
        TranscriptSegment(id=3, start_time=50.0, end_time=60.0, text="Sponsor B intro"),
    ]
    identifications = [
        Identification(transcript_segment_id=1, confidence=0.9),
        Identification(transcript_segment_id=2, confidence=0.9),
        Identification(transcript_segment_id=3, confidence=0.95),
    ]

    groups = ad_merger.merge(segments, identifications)

    assert len(groups) == 2
    assert groups[0].start_time == 0.0
    assert groups[0].end_time == 25.0
    assert "sponsor.com" in groups[0].keywords
