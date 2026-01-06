"""
Mixin for scraping agencies using OmpNetwork platform.

OmpNetwork (https://ompnetwork.org/) provides a hosted video streaming and
meeting management platform used by various municipalities. This mixin handles
the common API patterns used across OmpNetwork-powered sites.
"""

import json
from datetime import datetime

import scrapy
from city_scrapers_core.constants import NOT_CLASSIFIED
from city_scrapers_core.items import Meeting


class OmpNetworkMixin:
    """
    Mixin for scraping meeting data from OmpNetwork API endpoints.

    This mixin provides common functionality for parsing meeting data from
    OmpNetwork's JSON API. It should be used in conjunction with CityScrapersSpider.

    Required spider attributes:
        - site_id: The OmpNetwork site identifier (e.g., "312" for The Dalles)
        - category_id: The category ID for the specific agency/committee
        - agency: The agency name

    Optional spider attributes (with defaults):
        - timezone: Defaults to "America/Los_Angeles"
        - location: Defaults to The Dalles City Hall
    """

    # Default location for The Dalles meetings
    # Can be overridden in individual spiders if needed
    location = {
        "name": "The Dalles City Hall",
        "address": "313 Court St, The Dalles, OR 97058",
    }

    # Default timezone for The Dalles
    timezone = "America/Los_Angeles"

    # API has a maximum limit of ~150 items per request, use 100 to be safe
    page_size = 100

    @property
    def start_urls(self):
        """Return start URLs for the spider."""
        return [self.api_url]

    def _build_api_url(self, start=0, limit=100):
        """
        Build API URL with pagination parameters.

        Args:
            start: Offset for pagination
            limit: Number of items to fetch

        Returns:
            Full API URL with parameters
        """
        base_url = "https://thedalles-oregon.ompnetwork.org/api-cache"
        return (
            f"{base_url}/site/{self.site_id}/sessions"
            f"?category[]={self.category_id}&start={start}&limit={limit}"
        )

    @property
    def api_url(self):
        """Construct the initial API URL for the agency."""
        return self._build_api_url(start=0, limit=self.page_size)

    def parse(self, response):
        """
        Parse the API response and yield meeting items.

        This method handles pagination automatically to ensure all historical,
        current, and future meetings are scraped regardless of how many years
        pass or how many meetings accumulate in the system.

        Args:
            response: Scrapy response object containing JSON data

        Yields:
            Meeting items and follow-up requests for pagination
        """
        data = json.loads(response.text)

        # Parse all meetings in current page
        for item in data.get("results", []):
            meeting = Meeting(
                title=self._parse_title(item),
                description=self._parse_description(item),
                classification=self._parse_classification(item),
                start=self._parse_start(item),
                end=self._parse_end(item),
                all_day=self._parse_all_day(item),
                time_notes=self._parse_time_notes(item),
                location=self._parse_location(item),
                links=self._parse_links(item),
                source=self._parse_source(item),
            )

            meeting["status"] = self._get_status(meeting)
            meeting["id"] = self._get_id(meeting)

            yield meeting

        # Handle pagination if there are more results
        current_start = data.get("start", 0)
        current_size = data.get("size", 0)
        total_size = int(data.get("totalSize", 0))

        # Check if there are more pages to fetch
        if current_start + current_size < total_size:
            next_start = current_start + current_size
            next_url = self._build_api_url(start=next_start, limit=self.page_size)
            yield scrapy.Request(url=next_url, callback=self.parse)

    def _parse_title(self, item):
        """Parse or generate meeting title."""
        return item.get("title", "").strip() or self.agency

    def _parse_description(self, item):
        """Parse meeting description."""
        return ""

    def _parse_classification(self, item):
        """Parse or generate classification from allowed options."""
        return NOT_CLASSIFIED

    def _parse_start(self, item):
        """Parse start datetime from Unix timestamp."""
        timestamp = item.get("date")
        if timestamp:
            return datetime.fromtimestamp(int(timestamp))
        return None

    def _parse_end(self, item):
        """Parse end datetime."""
        return None

    def _parse_time_notes(self, item):
        """Parse any notes about the meeting time."""
        return ""

    def _parse_all_day(self, item):
        """Parse or generate all-day status."""
        return False

    def _parse_location(self, item):
        """
        Parse or generate location.

        OmpNetwork doesn't typically provide location data in the API,
        so we use the default location set in the class attribute.
        Individual spiders can override the location attribute if needed.
        """
        return self.location

    def _parse_links(self, item):
        """Parse meeting links (agendas, minutes, packets, videos)."""
        links = []

        # Add video link if available
        video_url = item.get("video_url") or ""
        video_url = video_url.strip() if video_url else ""
        if video_url:
            links.append({"href": video_url, "title": "Video"})

        # Add document links
        for doc in item.get("documents", []):
            doc_url = doc.get("url") or ""
            doc_url = doc_url.strip() if doc_url else ""
            doc_type = doc.get("type") or "Document"
            doc_type = doc_type.strip() if doc_type else "Document"
            if doc_url:
                links.append({"href": doc_url, "title": doc_type})

        return links

    def _parse_source(self, item):
        """Parse or generate source URL."""
        session_url = item.get("url") or ""
        session_url = session_url.strip() if session_url else ""
        if session_url:
            return f"https://thedalles-oregon.ompnetwork.org{session_url}"
        return self.api_url
