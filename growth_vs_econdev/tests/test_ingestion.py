"""Tests for the ingestion code. Run from the growth_vs_econdev folder:

    python -m pytest tests -v

These never call the real API or BigQuery. Instead, a fake fetch_page hands
back made-up pages, so the tests are fast, free, and always give the same answer.
"""
import json

from ingestion import worldbank_client
from ingestion.ingest import record_to_row

SAMPLE_RECORD = {
    "indicator": {"id": "NY.GDP.MKTP.KD.ZG", "value": "GDP growth (annual %)"},
    "country": {"id": "GH", "value": "Ghana"},
    "countryiso3code": "GHA",
    "date": "2025",
    "value": 5.95441714756899,
    "unit": "",
    "obs_status": "",
    "decimal": 1,
}


def fake_api(total_records, per_page):
    """Return a stand-in for fetch_page that serves `total_records` across pages."""
    pages = -(-total_records // per_page)  # ceiling division
    calls = []

    def fake_fetch_page(code, countries, start, end, page=1, per_page=per_page, retries=3):
        calls.append(page)
        first = (page - 1) * per_page
        last = min(page * per_page, total_records)
        records = [{"n": i} for i in range(first, last)]
        meta = {"page": page, "pages": pages, "total": total_records, "lastupdated": "2026-07-13"}
        return meta, records

    return fake_fetch_page, calls


# ---- TODO 1: paging loop ----------------------------------------------------

def test_single_page_returns_all_records(monkeypatch):
    fake, calls = fake_api(total_records=130, per_page=1000)
    monkeypatch.setattr(worldbank_client, "fetch_page", fake)

    records, last_updated = worldbank_client.fetch_indicator("X", ["GHA"], 2000, 2025)

    assert len(records) == 130
    assert last_updated == "2026-07-13"
    assert calls == [1], "only one page exists, so only one request should be made"


def test_multiple_pages_are_combined_in_order(monkeypatch):
    fake, calls = fake_api(total_records=130, per_page=50)
    monkeypatch.setattr(worldbank_client, "fetch_page", fake)

    records, _ = worldbank_client.fetch_indicator("X", ["GHA"], 2000, 2025, per_page=50)

    assert calls == [1, 2, 3], "should request pages 1, 2 and 3, then stop"
    assert len(records) == 130, "records from every page should be combined"
    assert [r["n"] for r in records] == list(range(130)), "no duplicates, nothing skipped"


def test_returns_a_plain_list_not_a_list_of_pages(monkeypatch):
    fake, _ = fake_api(total_records=60, per_page=50)
    monkeypatch.setattr(worldbank_client, "fetch_page", fake)

    records, _ = worldbank_client.fetch_indicator("X", ["GHA"], 2000, 2025, per_page=50)

    assert all(isinstance(r, dict) for r in records), "use list.extend, not list.append"


# ---- TODO 2: record_to_row --------------------------------------------------

def test_record_to_row_extracts_key_columns():
    row = record_to_row(SAMPLE_RECORD, "2026-07-13", "2026-10-05T14:03:00+00:00")

    assert row["indicator_id"] == "NY.GDP.MKTP.KD.ZG"
    assert row["country_iso3"] == "GHA", "use the 3-letter code, not country['id']"
    assert row["year"] == "2025", "keep the year as text; staging casts it"
    assert row["source_last_updated"] == "2026-07-13"
    assert row["ingested_at"] == "2026-10-05T14:03:00+00:00"


def test_record_to_row_keeps_the_whole_record_as_json_text():
    row = record_to_row(SAMPLE_RECORD, "2026-07-13", "2026-10-05T14:03:00+00:00")

    assert isinstance(row["payload"], str), "payload should be JSON text: json.dumps(record)"
    assert json.loads(row["payload"]) == SAMPLE_RECORD, "payload should hold the full, unchanged record"


def test_record_to_row_has_exactly_the_schema_columns():
    row = record_to_row(SAMPLE_RECORD, "2026-07-13", "2026-10-05T14:03:00+00:00")

    assert set(row) == {"indicator_id", "country_iso3", "year", "payload",
                        "source_last_updated", "ingested_at"}


def test_record_to_row_keeps_null_values():
    missing = {**SAMPLE_RECORD, "value": None}
    row = record_to_row(missing, "2026-07-13", "2026-10-05T14:03:00+00:00")

    assert json.loads(row["payload"])["value"] is None, "null means 'no data'; keep it"
