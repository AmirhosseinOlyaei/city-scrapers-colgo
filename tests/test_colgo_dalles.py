"""
Tests for The Dalles spiders using OmpNetwork API.
"""

from datetime import datetime
from os.path import dirname, join

from city_scrapers_core.constants import BOARD, CITY_COUNCIL, COMMISSION
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.colgo_dalles import (
    ColgoDallesCityCouncilSpider,
    ColgoDallesHistoricLandmarksSpider,
    ColgoDallesInformationalSpider,
    ColgoDallesPlanningCommissionSpider,
    ColgoDallesUrbanRenewalSpider,
)

test_response = file_response(
    join(dirname(__file__), "files", "colgo_dalles_city_council.json"),
    url="https://thedalles-oregon.ompnetwork.org/api-cache/site/312/sessions?category[]=214&start=0&limit=100",  # noqa
)
spider = ColgoDallesCityCouncilSpider()

# Freeze time to a date between past and future meetings in the test data
# This allows us to test both "passed" and "tentative" status values
# Test data is fetched from live API and will contain current/future meetings
# Freezing at 2025-12-16 to ensure consistent test results
freezer = freeze_time("2025-12-16")
freezer.start()

# Filter out Request objects - only get Meeting items
parsed_items = [
    item
    for item in spider.parse(test_response)
    if hasattr(item, "__getitem__") and "title" in item
]

freezer.stop()


def test_count():
    """Test that the expected number of items are returned."""
    assert len(parsed_items) == 10


def test_title():
    """Test that titles are parsed correctly."""
    assert (
        parsed_items[0]["title"]
        == "City Council Meeting January 12, 2026 - Live Stream"
    )


def test_description():
    """Test that descriptions are empty strings."""
    assert parsed_items[0]["description"] == ""


def test_start():
    """Test that start times are parsed correctly."""
    # API returns UTC timestamp, parsed as local time
    assert parsed_items[0]["start"] == datetime(2026, 1, 12, 17, 30, 0)


def test_end():
    """Test that end times are None."""
    assert parsed_items[0]["end"] is None


def test_time_notes():
    """Test that time notes are empty strings."""
    assert parsed_items[0]["time_notes"] == ""


def test_id():
    """Test that IDs are generated correctly."""
    assert (
        parsed_items[0]["id"]
        == "colgo_dalles_city_council/202601121730/x/city_council_meeting_january_12_2026_live_stream"  # noqa
    )


def test_status():
    """Test that status is set correctly."""
    # First meeting is in future (2026-01-12), frozen time is 2025-12-16
    assert parsed_items[0]["status"] == "tentative"
    # 10th meeting is in August 2025, before frozen time, so it's passed
    assert parsed_items[9]["status"] == "passed"


def test_location():
    """Test that location is set correctly."""
    assert parsed_items[0]["location"] == {
        "name": "The Dalles City Hall",
        "address": "313 Court St, The Dalles, OR 97058",
    }


def test_source():
    """Test that source URLs are parsed correctly."""
    assert (
        parsed_items[0]["source"]
        == "https://thedalles-oregon.ompnetwork.org/sessions/332148/city-council-meeting-january-12-2026-live-stream"  # noqa
    )


def test_links():
    """Test that links are parsed correctly."""
    links = parsed_items[0]["links"]
    # First meeting has 2 links (Agenda and Packet, no video yet for future meeting)
    assert len(links) == 2
    assert links[0]["title"] == "Agenda"
    assert links[1]["title"] == "Packet"
    assert "cc_2026-01-12_city_council_agenda.pdf" in links[0]["href"]


def test_classification():
    """Test that classification is set correctly for City Council."""
    assert parsed_items[0]["classification"] == CITY_COUNCIL


def test_all_day():
    """Test that all_day is False."""
    assert parsed_items[0]["all_day"] is False


# Test other spiders to ensure they are configured correctly


def test_informational_spider():
    """Test Informational/Town Hall spider configuration."""
    spider = ColgoDallesInformationalSpider()
    assert spider.name == "colgo_dalles_informational"
    assert spider.agency == "The Dalles Informational or Town Hall Meetings"
    assert spider.category_id == "215"


def test_planning_commission_spider():
    """Test Planning Commission spider configuration."""
    spider = ColgoDallesPlanningCommissionSpider()
    assert spider.name == "colgo_dalles_planning_commission"
    assert spider.agency == "The Dalles Planning Commission"
    assert spider.category_id == "216"
    # Test classification for planning commission
    assert spider._parse_classification({}) == COMMISSION


def test_urban_renewal_spider():
    """Test Urban Renewal Agency spider configuration."""
    spider = ColgoDallesUrbanRenewalSpider()
    assert spider.name == "colgo_dalles_urban_renewal"
    assert spider.agency == "The Dalles Urban Renewal Agency"
    assert spider.category_id == "218"
    # Test classification for urban renewal
    assert spider._parse_classification({}) == BOARD


def test_historic_landmarks_spider():
    """Test Historic Landmarks Commission spider configuration."""
    spider = ColgoDallesHistoricLandmarksSpider()
    assert spider.name == "colgo_dalles_historic_landmarks"
    assert spider.agency == "The Dalles Historic Landmarks Commission"
    assert spider.category_id == "217"
    # Test classification for historic landmarks
    assert spider._parse_classification({}) == COMMISSION
