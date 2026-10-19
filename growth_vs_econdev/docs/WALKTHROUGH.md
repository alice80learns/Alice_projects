# 5-minute walkthrough: one number, from chart to API

The demo traces **one dot on the main chart** back through every layer to the raw API record. It shows the whole pipeline in five minutes and proves every number can be traced back to its source.

**The number:** Rwanda's poverty fell **25.2 percentage points** between its 2016 and 2023 surveys, while the economy grew **6.6% a year**. It's the "RWA 2016–23" dot in the scatter, at x = 6.6, y = −3.6.

Before the demo, open BigQuery in the browser with the 4 queries below ready in separate tabs, plus the notebook and the dbt docs site (`dbt docs serve`).

---

## 0:00 — The question (30 seconds)

> "I wanted to know whether economic growth turns into better lives in five African economies. I built an ELT pipeline from the World Bank API into BigQuery, transformed it with dbt, and answered the question in a notebook. The short answer is: only partly."

## 0:30 — The chart (1 minute)

Show the scatter in `notebooks/analysis.ipynb` (section 3).

> "Each dot is one pair of back-to-back poverty surveys in one country. Poverty is only surveyed every few years, so I compare survey to survey instead of inventing the years in between. Growth and poverty reduction barely moved together: the correlation is about −0.1. Let's take this dot: Rwanda, 2016 to 2023."

Point out the y-axis is **per year**: −25.2 points ÷ 7 years = −3.6.

## 1:30 — The mart (45 seconds)

```sql
select country_iso3, start_year, end_year, poverty_start_pct, poverty_end_pct,
       poverty_change_pp, avg_gdp_growth_pct
from `econdev-portfolio-alice.dbt_dev.fct_poverty_survey_spans`
where country_iso3 = 'RWA' and start_year = 2016;
```

| start_year | end_year | poverty_start_pct | poverty_end_pct | poverty_change_pp | avg_gdp_growth_pct |
| --- | --- | --- | --- | --- | --- |
| 2016 | 2023 | 63.8 | 38.6 | −25.2 | 6.58 |

> "This mart has one row per pair of surveys. The poverty change is just end minus start. The growth is the average of the years *after* the first survey up to the second one, 2017 to 2023, so the first survey's year isn't counted twice."

## 2:15 — The intermediate model (30 seconds)

```sql
select country_iso3, year, poverty_pct, gdp_growth_pct
from `econdev-portfolio-alice.dbt_dev.int_indicators_pivoted`
where country_iso3 = 'RWA' and year in (2016, 2023);
```

| year | poverty_pct | gdp_growth_pct |
| --- | --- | --- |
| 2016 | 63.8 | 5.66 |
| 2023 | 38.6 | 8.56 |

> "Here the data is pivoted to one row per country-year, every indicator side by side. A custom dbt test checks that this pivot never loses a value."

## 2:45 — Staging (30 seconds)

```sql
select country_iso3, indicator_id, indicator_name, year, value
from `econdev-portfolio-alice.dbt_dev.stg_worldbank__indicators`
where country_iso3 = 'RWA' and indicator_id = 'SI.POV.DDAY' and year in (2016, 2023);
```

| indicator_id | indicator_name | year | value |
| --- | --- | --- | --- |
| SI.POV.DDAY | poverty_pct | 2016 | 63.8 |
| SI.POV.DDAY | poverty_pct | 2023 | 38.6 |

> "Staging is long: one row per country, indicator and year. It only renames, casts types and pulls fields out of the JSON. No filtering and no business logic, so it's a faithful, typed copy of the source."

## 3:15 — Raw (45 seconds)

```sql
select indicator_id, country_iso3, year, payload, source_last_updated, ingested_at
from `econdev-portfolio-alice.raw.worldbank_indicators`
where country_iso3 = 'RWA' and indicator_id = 'SI.POV.DDAY' and year = '2023';
```

The `payload` column holds the API record exactly as it arrived:

```json
{"indicator": {"id": "SI.POV.DDAY", "value": "Poverty headcount ratio at $3.00 a day (2021 PPP) (% of population)"},
 "country": {"id": "RW", "value": "Rwanda"}, "countryiso3code": "RWA", "date": "2023", "value": 38.6, ...}
```

> "The raw table stores every record unchanged, as JSON text, plus when the World Bank last revised it and when my pipeline loaded it. If a transform has a bug, I fix the SQL and rebuild. I never have to call the API again."

## 4:00 — The source (20 seconds)

Open in the browser:
`https://api.worldbank.org/v2/country/RWA/indicator/SI.POV.DDAY?format=json&date=2023`

> "And here's the same 38.6 straight from the World Bank."

## 4:20 — How I know it's right (40 seconds)

Show the lineage graph in the dbt docs site.

> "Every layer is tested: 48 dbt tests, including a grain test on every model so duplicates can't silently inflate the numbers. I broke the pivot on purpose to make sure the tests catch it, and `dbt build` skipped both marts. The whole thing rebuilds from scratch with two commands: `python -m ingestion.ingest` and `dbt build`."

## Likely follow-up questions

- **"Why not fill in poverty for the missing years?"** Because those values would be invented. I built a separate mart at the survey-pair grain instead.
- **"Does growth cause poverty reduction?"** The data can't say. It shows they moved together loosely. South Africa cut poverty with almost no growth, so other factors were clearly at work.
- **"What would you do next?"** Add population to get growth per person, add a better jobs measure, and schedule the pipeline monthly with Airflow.
- **"What happens when the World Bank revises its data?"** The next run replaces the raw table, and `source_last_updated` records the revision date. `dbt source freshness` warns if the data is more than 35 days old.
