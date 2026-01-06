"""
City scrapers for The Dalles, Oregon government meetings.

This module contains spiders for scraping meetings from The Dalles city government
using the OmpNetwork platform API. The following agencies are covered:
- City Council
- Informational/Town Hall meetings
- Planning Commission
- Urban Renewal Agency
- Historic Landmarks Commission
"""

from city_scrapers_core.constants import BOARD, CITY_COUNCIL, COMMISSION, NOT_CLASSIFIED
from city_scrapers_core.spiders import CityScrapersSpider

from city_scrapers.mixins.ompnetwork import OmpNetworkMixin


class ColgoDallesCityCouncilSpider(OmpNetworkMixin, CityScrapersSpider):
    """Spider for The Dalles City Council meetings."""

    name = "colgo_dalles_city_council"
    agency = "The Dalles City Council"
    site_id = "312"
    category_id = "214"

    def _parse_classification(self, item):
        """Parse classification as CITY_COUNCIL."""
        return CITY_COUNCIL


class ColgoDallesInformationalSpider(OmpNetworkMixin, CityScrapersSpider):
    """Spider for The Dalles Informational/Town Hall meetings."""

    name = "colgo_dalles_informational"
    agency = "The Dalles Informational or Town Hall Meetings"
    site_id = "312"
    category_id = "215"

    def _parse_classification(self, item):
        """Parse classification as NOT_CLASSIFIED."""
        return NOT_CLASSIFIED


class ColgoDallesPlanningCommissionSpider(OmpNetworkMixin, CityScrapersSpider):
    """Spider for The Dalles Planning Commission meetings."""

    name = "colgo_dalles_planning_commission"
    agency = "The Dalles Planning Commission"
    site_id = "312"
    category_id = "216"

    def _parse_classification(self, item):
        """Parse classification as COMMISSION."""
        return COMMISSION


class ColgoDallesUrbanRenewalSpider(OmpNetworkMixin, CityScrapersSpider):
    """Spider for The Dalles Urban Renewal Agency meetings."""

    name = "colgo_dalles_urban_renewal"
    agency = "The Dalles Urban Renewal Agency"
    site_id = "312"
    category_id = "218"

    def _parse_classification(self, item):
        """Parse classification as BOARD."""
        return BOARD


class ColgoDallesHistoricLandmarksSpider(OmpNetworkMixin, CityScrapersSpider):
    """Spider for The Dalles Historic Landmarks Commission meetings."""

    name = "colgo_dalles_historic_landmarks"
    agency = "The Dalles Historic Landmarks Commission"
    site_id = "312"
    category_id = "217"

    def _parse_classification(self, item):
        """Parse classification as COMMISSION."""
        return COMMISSION
