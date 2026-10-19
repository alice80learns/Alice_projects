"""Extract World Bank indicators and load them, unchanged, into BigQuery.

Run from the growth_vs_econdev folder:
    python -m ingestion.ingest

This is the "EL" of ELT: no cleaning happens here. Each API record is stored
as raw JSON text, plus a few columns that make it easy to find. All cleaning
and reshaping happens later in dbt, so if a transform has a bug, the raw data
is still here to rebuild from.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml
from google.cloud import bigquery

from ingestion.worldbank_client import fetch_indicator

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "indicators.yml"

# The raw table's columns. Everything is kept as text except ingested_at:
# the raw layer mirrors the source, and staging decides the real types.
RAW_SCHEMA = [
    bigquery.SchemaField("indicator_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("country_iso3", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("year", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("payload", "STRING", mode="REQUIRED",
                         description="The full API record as JSON text"),
    bigquery.SchemaField("source_last_updated", "STRING",
                         description="When the World Bank last revised this indicator"),
    bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED",
                         description="When this pipeline run loaded the row (UTC)"),
]

log = logging.getLogger("ingest")


def load_config(path=CONFIG_PATH):
    return yaml.safe_load(Path(path).read_text())


def record_to_row(record, last_updated, ingested_at):
    """Turn one API record into one row for the raw table.

    record       -> one record dict from the API, e.g.
                    {"indicator": {"id": "NY.GDP.MKTP.KD.ZG", "value": "GDP growth (annual %)"},
                     "country": {"id": "GH", "value": "Ghana"},
                     "countryiso3code": "GHA", "date": "2025", "value": 5.95, ...}
    last_updated -> the indicator's lastupdated date, e.g. "2026-07-13"
    ingested_at  -> this run's timestamp as text, e.g. "2026-10-05T14:03:00+00:00"

    Returns a dict whose keys match RAW_SCHEMA above.
    """
    return {
        "indicator_id": record["indicator"]["id"],    # nested: indicator -> id
        "country_iso3": record["countryiso3code"],    # 3-letter code, matches config
        "year": record["date"],                       # kept as text; staging casts it
        "payload": json.dumps(record),                # the full record, unchanged
        "source_last_updated": last_updated,
        "ingested_at": ingested_at,
    }


def load_to_bigquery(rows, project, table):
    """Replace the raw table's contents with `rows`.

    WRITE_TRUNCATE means "replace everything in the table". That makes the load
    idempotent: run it twice and you still have one copy of each row, never
    duplicates. Appending (WRITE_APPEND) would double the data on every rerun.
    """
    client = bigquery.Client(project=project)
    job_config = bigquery.LoadJobConfig(
        schema=RAW_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_json(rows, f"{project}.{table}", job_config=job_config)
    job.result()  # wait for the load to finish; raises if it failed
    return client.get_table(f"{project}.{table}").num_rows


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config()
    countries = config["countries"]
    start, end = config["start_year"], config["end_year"]
    ingested_at = datetime.now(timezone.utc).isoformat()

    rows = []
    for code in config["indicators"]:
        records, last_updated = fetch_indicator(code, countries, start, end)
        nulls = sum(1 for r in records if r["value"] is None)
        log.info("%s: %d records fetched, %d with null value", code, len(records), nulls)
        rows.extend(record_to_row(r, last_updated, ingested_at) for r in records)

    # Sanity check before touching the warehouse: every country x indicator x year.
    expected = len(countries) * len(config["indicators"]) * (end - start + 1)
    if len(rows) != expected:
        raise RuntimeError(f"Expected {expected} rows but built {len(rows)}; not loading")

    bq = config["bigquery"]
    total = load_to_bigquery(rows, bq["project"], bq["raw_table"])
    log.info("Loaded %d rows into %s.%s", total, bq["project"], bq["raw_table"])


if __name__ == "__main__":
    main()
