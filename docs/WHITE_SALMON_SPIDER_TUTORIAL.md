# White Salmon Spider Factory Tutorial

A step-by-step guide on how the White Salmon, WA meeting scrapers were built using the spider factory (mixin) pattern.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
   - [What We Built](#what-we-built)
   - [Why Spider Factory Pattern](#why-spider-factory-pattern)
2. [Understanding the Target Website](#2-understanding-the-target-website)
   - [Analyzing the Calendar Page](#analyzing-the-calendar-page)
   - [Analyzing the Meeting Detail Page](#analyzing-the-meeting-detail-page)
   - [Identifying Agency IDs](#identifying-agency-ids)
3. [Building the Mixin](#3-building-the-mixin)
   - [File Structure](#file-structure)
   - [The Metaclass Pattern](#the-metaclass-pattern)
   - [Base Configuration](#base-configuration)
   - [Request Generation](#request-generation)
   - [Parsing Calendar Pages](#parsing-calendar-pages)
   - [Parsing Meeting Details](#parsing-meeting-details)
   - [Helper Methods](#helper-methods)
4. [Creating Individual Spiders](#4-creating-individual-spiders)
   - [City Council Spider](#city-council-spider)
   - [Civil Service Commission Spider](#civil-service-commission-spider)
   - [Planning Commission Spider](#planning-commission-spider)
5. [Writing Tests](#5-writing-tests)
   - [Creating HTML Fixtures](#creating-html-fixtures)
   - [Testing Source Data vs Output](#testing-source-data-vs-output)
   - [Test Structure](#test-structure)
6. [Code Review and Fixes](#6-code-review-and-fixes)
   - [The Location Bug](#the-location-bug)
   - [Import Organization](#import-organization)
   - [Lessons Learned](#lessons-learned)
7. [Pull Request Process](#7-pull-request-process)
   - [PR Description Template](#pr-description-template)
   - [Manual Testing Steps](#manual-testing-steps)
8. [Key Takeaways](#8-key-takeaways)

---

## 1. Project Overview

### What We Built

We created scrapers for three White Salmon, WA government agencies:

| Spider Name | Agency | Agency ID |
|-------------|--------|-----------|
| `colgo_white_salmon_city_council` | City Council of White Salmon | 27 |
| `colgo_white_salmon_civil_service` | White Salmon Civil Service Commission | 231 |
| `colgo_white_salmon_planning` | White Salmon Planning Commission | 28 |

All three agencies share the same website structure (Drupal calendar), so we used a **spider factory pattern** with a shared mixin.

### Why Spider Factory Pattern

Instead of duplicating code across three spiders, we:
- Created ONE mixin (`WhiteSalmonMixin`) with all the parsing logic
- Created THREE minimal spider files that inherit from the mixin
- Each spider only defines: `name`, `agency`, `agency_id`

**Benefits:**
- DRY (Don't Repeat Yourself)
- Single place to fix bugs
- Easy to add new agencies

---

## 2. Understanding the Target Website

Before writing any code, we analyzed the website structure.

### Analyzing the Calendar Page

**URL Pattern:**
```
https://www.whitesalmonwa.gov/calendar/month/{YYYY-MM}?field_microsite_tid=All&field_microsite_tid_1={agency_id}
```

**Example:** January 2025 for City Council (ID=27)
```
https://www.whitesalmonwa.gov/calendar/month/2025-01?field_microsite_tid=All&field_microsite_tid_1=27
```

**Key HTML Structure (calendar):**
```html
<div class="view-item view-item-calendar">
  <div class="views-field views-field-title">
    <a href="/citycouncil/page/city-council-meeting-121">City Council Meeting</a>
  </div>
</div>
```

**CSS Selector for meeting links:**
```python
".view-item-calendar .views-field-title a::attr(href)"
```

### Analyzing the Meeting Detail Page

**Key HTML Elements:**

1. **Title:**
```html
<h1 id="page-title">City Council Meeting</h1>
```

2. **Date/Time (ISO format in attribute):**
```html
<span class="date-display-single" content="2025-12-17T18:00:00-08:00">6:00pm</span>
```

3. **Location (in body text):**
```html
<p>Location: City's Council Chambers, 119 NE Church Ave, White Salmon, WA 98672</p>
```

4. **Links (agenda, packet, video):**
```html
<div class="field-name-field-agenda-link">
  <a href="...">Agenda</a>
</div>
```

### Identifying Agency IDs

Found in the filter dropdown on the calendar page:

```html
<select name="field_microsite_tid_1">
  <option value="27">-City Council</option>
  <option value="231">-Civil Service Commission</option>
  <option value="28">-Planning Commission</option>
</select>
```

---

## 3. Building the Mixin

### File Structure

```
city_scrapers/
├── mixins/
│   ├── __init__.py
│   └── white_salmon.py      # Shared mixin
└── spiders/
    ├── __init__.py
    ├── colgo_white_salmon_city_council.py
    ├── colgo_white_salmon_civil_service.py
    └── colgo_white_salmon_planning.py
```

### The Metaclass Pattern

We use a metaclass to **enforce** that child classes define required variables:

```python
class WhiteSalmonMixinMeta(type):
    def __init__(cls, name, bases, dct):
        required_static_vars = ["agency", "name", "agency_id"]
        missing_vars = [var for var in required_static_vars if var not in dct]

        if missing_vars:
            raise NotImplementedError(
                f"{name} must define: {', '.join(missing_vars)}"
            )
        super().__init__(name, bases, dct)
```

**Why?** If someone creates a spider and forgets to set `agency_id`, they get a clear error immediately, not a confusing runtime bug.

### Base Configuration

```python
class WhiteSalmonMixin(CityScrapersSpider, metaclass=WhiteSalmonMixinMeta):
    # Placeholders - child classes MUST override these
    name = None
    agency = None
    agency_id = None

    # Configuration
    timezone = "America/Los_Angeles"
    base_url = "https://www.whitesalmonwa.gov"
    calendar_url = (
        "https://www.whitesalmonwa.gov/calendar/month/{month}"
        "?field_microsite_tid=All&field_microsite_tid_1={agency_id}"
    )

    # Fallback location (parsed from source when available)
    default_location = {"name": "", "address": ""}
```

### Request Generation

Scrape current month + next 2 months:

```python
def start_requests(self):
    today = datetime.now()
    for i in range(3):  # Current + 2 future months
        target_date = today + relativedelta(months=i)
        month_str = target_date.strftime("%Y-%m")
        url = self.calendar_url.format(month=month_str, agency_id=self.agency_id)
        yield scrapy.Request(url=url, callback=self.parse)
```

### Parsing Calendar Pages

Extract links to meeting detail pages:

```python
def parse(self, response):
    meeting_links = response.css(
        ".view-item-calendar .views-field-title a::attr(href)"
    ).getall()

    for link in meeting_links:
        full_url = response.urljoin(link)
        yield scrapy.Request(url=full_url, callback=self.parse_meeting)
```

### Parsing Meeting Details

Build the `Meeting` item from detail page:

```python
def parse_meeting(self, response):
    title = self._parse_title(response)
    start = self._parse_start(response)

    if not start:
        self.logger.warning(f"Skipping meeting with no start time: {response.url}")
        return

    meeting = Meeting(
        title=title,
        description=self._parse_description(response),
        classification=self._parse_classification(title),
        start=start,
        end=None,
        all_day=False,
        time_notes="",
        location=self._parse_location(response),  # Parsed from source!
        links=self._parse_links(response),
        source=response.url,
    )

    meeting["status"] = self._get_status(meeting, text=title)
    meeting["id"] = self._get_id(meeting)

    yield meeting
```

### Helper Methods

**Parse Start Time (from ISO attribute):**
```python
def _parse_start(self, response):
    dt_str = response.css(
        ".calendar-date span.date-display-single::attr(content)"
    ).get()

    if dt_str:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)  # Return naive datetime
    return None
```

**Parse Location (from body text using regex):**
```python
def _parse_location(self, response):
    body_text = response.css(".field-name-body .field-item").get() or ""

    location_match = re.search(
        r"Location:\s*([^,]+),\s*(.+?)(?:</p>|<br|$)",
        body_text,
        re.IGNORECASE,
    )

    if location_match:
        name = location_match.group(1).strip()
        address = re.sub(r"<[^>]+>", "", location_match.group(2)).strip()
        return {"name": name, "address": address}

    return self.default_location
```

---

## 4. Creating Individual Spiders

Each spider is minimal - just configuration:

### City Council Spider

```python
# city_scrapers/spiders/colgo_white_salmon_city_council.py
from city_scrapers_core.constants import CITY_COUNCIL
from city_scrapers.mixins.white_salmon import WhiteSalmonMixin


class ColgoWhiteSalmonCityCouncilSpider(WhiteSalmonMixin):
    name = "colgo_white_salmon_city_council"
    agency = "City Council of White Salmon"
    agency_id = "27"
    classification = CITY_COUNCIL
```

### Civil Service Commission Spider

```python
# city_scrapers/spiders/colgo_white_salmon_civil_service.py
from city_scrapers_core.constants import COMMISSION
from city_scrapers.mixins.white_salmon import WhiteSalmonMixin


class ColgoWhiteSalmonCivilServiceSpider(WhiteSalmonMixin):
    name = "colgo_white_salmon_civil_service"
    agency = "White Salmon Civil Service Commission"
    agency_id = "231"
    classification = COMMISSION
```

### Planning Commission Spider

```python
# city_scrapers/spiders/colgo_white_salmon_planning.py
from city_scrapers_core.constants import COMMISSION
from city_scrapers.mixins.white_salmon import WhiteSalmonMixin


class ColgoWhiteSalmonPlanningSpider(WhiteSalmonMixin):
    name = "colgo_white_salmon_planning"
    agency = "White Salmon Planning Commission"
    agency_id = "28"
    classification = COMMISSION
```

---

## 5. Writing Tests

### Creating HTML Fixtures

We save real HTML from the website as test fixtures:

```
tests/files/
├── colgo_white_salmon_city_council_calendar.html  # Calendar page
└── colgo_white_salmon_city_council_detail.html    # Meeting detail page
```

**How to capture:**
```bash
curl "https://www.whitesalmonwa.gov/calendar/month/2025-01?field_microsite_tid=All&field_microsite_tid_1=27" \
  > tests/files/colgo_white_salmon_city_council_calendar.html
```

### Testing Source Data vs Output

**Key principle:** Test that given SOURCE HTML, the spider produces expected OUTPUT.

```
┌─────────────────┐      parse()       ┌──────────────────┐
│  Calendar HTML  │  ─────────────────▶│  Detail Page URLs │
│   (fixture)     │                    │    (requests)     │
└─────────────────┘                    └──────────────────┘

┌─────────────────┐   parse_meeting()  ┌──────────────────┐
│   Detail HTML   │  ─────────────────▶│   Meeting Item   │
│   (fixture)     │                    │    (output)      │
└─────────────────┘                    └──────────────────┘
```

We test BOTH stages:

1. **Calendar parsing:** Does `parse()` extract correct meeting links?
2. **Detail parsing:** Does `parse_meeting()` extract correct meeting data?

### Test Structure

```python
# tests/test_colgo_white_salmon_city_council.py

from datetime import datetime
from os.path import dirname, join
from city_scrapers_core.constants import CITY_COUNCIL, PASSED
from city_scrapers_core.utils import file_response
from freezegun import freeze_time

from city_scrapers.spiders.colgo_white_salmon_city_council import (
    ColgoWhiteSalmonCityCouncilSpider,
)

spider = ColgoWhiteSalmonCityCouncilSpider()

# ===========================================
# Test 1: Calendar Parsing (source → URLs)
# ===========================================
calendar_response = file_response(
    join(dirname(__file__), "files", "colgo_white_salmon_city_council_calendar.html"),
    url="https://www.whitesalmonwa.gov/calendar/month/2025-01...",
)

calendar_requests = list(spider.parse(calendar_response))

def test_calendar_request_count():
    """Calendar should extract at least one meeting link."""
    assert len(calendar_requests) >= 1

def test_calendar_request_url():
    """URLs should point to meeting detail pages."""
    urls = [req.url for req in calendar_requests]
    assert any("city-council-meeting" in url for url in urls)


# ===========================================
# Test 2: Detail Parsing (source → Meeting)
# ===========================================
detail_response = file_response(
    join(dirname(__file__), "files", "colgo_white_salmon_city_council_detail.html"),
    url="https://www.whitesalmonwa.gov/citycouncil/page/city-council-meeting-152",
)

# Freeze time to control status calculation
freezer = freeze_time("2025-12-22")
freezer.start()
parsed_items = list(spider.parse_meeting(detail_response))
freezer.stop()

parsed_item = parsed_items[0]

def test_title():
    assert parsed_item["title"] == "City Council Meeting"

def test_start():
    assert parsed_item["start"] == datetime(2025, 12, 17, 18, 0)

def test_location():
    assert parsed_item["location"] == {
        "name": "City's Council Chambers",
        "address": "119 NE Church Ave, White Salmon, WA 98672",
    }

# ... more tests for each field
```

**Why `freeze_time`?**
Meeting status depends on current date:
- Past meeting → `PASSED`
- Future meeting → `TENTATIVE`
- Cancelled → `CANCELLED`

By freezing time, tests are deterministic.

---

## 6. Code Review and Fixes

### The Location Bug

**What happened:**
- I hardcoded: `"100 N Main St., White Salmon, WA 98672"` (City Hall)
- The HTML fixture showed: `"119 NE Church Ave, White Salmon, WA 98672"` (Council Chambers)

**Root cause:** Used external info (spreadsheet notes) instead of SOURCE DATA.

**Fix:** Parse location from HTML instead of hardcoding:

```python
def _parse_location(self, response):
    body_text = response.css(".field-name-body .field-item").get() or ""
    
    location_match = re.search(
        r"Location:\s*([^,]+),\s*(.+?)(?:</p>|<br|$)",
        body_text,
        re.IGNORECASE,
    )
    
    if location_match:
        return {
            "name": location_match.group(1).strip(),
            "address": re.sub(r"<[^>]+>", "", location_match.group(2)).strip()
        }
    
    return self.default_location
```

### Import Organization

**Issue:** Imports inside methods add overhead and break conventions.

**Before (bad):**
```python
def request(self, url, callback):
    import scrapy  # Inside method!
    return scrapy.Request(url=url, callback=callback)

def _get_status(self, item, text=""):
    if "cancel" in text.lower():
        from city_scrapers_core.constants import CANCELLED  # Inside method!
        return CANCELLED
```

**After (good):**
```python
# All imports at module level
import scrapy
from city_scrapers_core.constants import CANCELLED, CITY_COUNCIL, ...

def request(self, url, callback):
    return scrapy.Request(url=url, callback=callback)

def _get_status(self, item, text=""):
    if "cancel" in text.lower():
        return CANCELLED
```

### Lessons Learned

1. **Always verify against source data** - Don't assume, check the HTML
2. **Test both parsing stages** - Calendar → URLs AND Detail → Meeting
3. **Keep imports at module level** - Python convention, better performance
4. **Use fixtures from real pages** - Ensures tests match actual website

---

## 7. Pull Request Process

### PR Description Template

```markdown
## What's this PR do?
Adds a spider factory (mixin pattern) to scrape meeting information from three 
White Salmon, WA agencies:
- City Council (`colgo_white_salmon_city_council`)
- Civil Service Commission (`colgo_white_salmon_civil_service`)
- Planning Commission (`colgo_white_salmon_planning`)

## Why are we doing this?
Requested based on the following spreadsheet: [Scraper Audit Nov 2025](...)

## Steps to manually test
1. `pipenv sync --dev`
2. `pipenv shell`
3. `scrapy crawl colgo_white_salmon_city_council -O test_output.csv`
4. `pytest tests/test_colgo_white_salmon_city_council.py -v`

## Are there any smells or added technical debt to note?
- Uses mixin pattern with metaclass enforcement
- Scrapes current month + 2 future months
```

### Manual Testing Steps

```bash
# Install dependencies
pipenv sync --dev
pipenv shell

# Run spider
scrapy crawl colgo_white_salmon_city_council -O test_output.csv

# Check output
cat test_output.csv

# Run tests
pytest tests/test_colgo_white_salmon_city_council.py -v

# Check linting
flake8 city_scrapers/mixins/white_salmon.py
```

---

## 8. Key Takeaways

| Principle | Application |
|-----------|-------------|
| **DRY** | One mixin, three spiders |
| **Test source data** | Use HTML fixtures, test both parsing stages |
| **Verify assumptions** | Check HTML, don't trust external docs |
| **Imports at top** | Module-level imports only |
| **Metaclass enforcement** | Catch missing config early |
| **Fork workflow** | Fork → Clone → Branch → PR |

**Files Created:**

| File | Purpose |
|------|---------|
| `city_scrapers/mixins/white_salmon.py` | Shared parsing logic |
| `city_scrapers/spiders/colgo_white_salmon_city_council.py` | City Council spider |
| `city_scrapers/spiders/colgo_white_salmon_civil_service.py` | Civil Service spider |
| `city_scrapers/spiders/colgo_white_salmon_planning.py` | Planning spider |
| `tests/test_colgo_white_salmon_city_council.py` | Test suite |
| `tests/files/colgo_white_salmon_city_council_calendar.html` | Calendar fixture |
| `tests/files/colgo_white_salmon_city_council_detail.html` | Detail fixture |

**PR:** https://github.com/City-Bureau/city-scrapers-colgo/pull/4

---

*This tutorial was generated to document the development process of the White Salmon spider factory project.*
