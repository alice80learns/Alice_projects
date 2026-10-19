"""Small client for the World Bank Indicators API (https://api.worldbank.org/v2).

The API returns every response as a 2-item list: [page metadata, list of records].
Large results are split across pages, so callers must keep asking until they
have every page (see fetch_indicator).
"""
import logging
import time

import requests

BASE_URL = "https://api.worldbank.org/v2"

log = logging.getLogger(__name__)


def fetch_page(code, countries, start, end, page=1, per_page=1000, retries=3):
    """Fetch ONE page of records for one indicator.

    Returns (meta, records):
      meta    -> dict such as {"page": 1, "pages": 3, "total": 130, "lastupdated": "2026-07-13", ...}
      records -> list of record dicts (can be empty)

    Network problems and server errors (5xx) are retried with a growing pause
    ("exponential backoff"): wait 2s, then 4s. Client errors such as a 400 for a
    bad indicator code are NOT retried, because asking again won't fix them.
    """
    url = f"{BASE_URL}/country/{';'.join(countries)}/indicator/{code}"
    params = {"format": "json", "date": f"{start}:{end}", "page": page, "per_page": per_page}

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code < 500:
                resp.raise_for_status()  # 4xx: fail immediately, retrying won't help
                break
            log.warning("Server error %s on %s page %s", resp.status_code, code, page)
        except (requests.ConnectionError, requests.Timeout) as exc:
            log.warning("Network problem on %s page %s: %s", code, page, exc)

        if attempt == retries:
            raise RuntimeError(f"Gave up on {code} page {page} after {retries} attempts")
        time.sleep(2 ** attempt)

    body = resp.json()
    # An unknown indicator code comes back as a 1-item list holding an error message.
    if len(body) < 2:
        raise ValueError(f"Unexpected API response for {code}: {body}")
    meta, records = body
    return meta, records or []


def fetch_indicator(code, countries, start, end, per_page=1000):
    """Fetch EVERY page for one indicator.

    Returns (records, last_updated):
      records      -> one combined list with the records from all pages
      last_updated -> meta["lastupdated"], the date the World Bank last revised
                      this indicator (the same on every page)
    """
    records, page = [], 1
    while True:
        # fetch_page wraps the API call with retries, unlike a bare requests.get
        meta, rows = fetch_page(code, countries, start, end, page=page, per_page=per_page)
        records.extend(rows)
        if page >= meta["pages"]:
            return records, meta["lastupdated"]
        page += 1
