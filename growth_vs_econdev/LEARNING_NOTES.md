# Learning Notes: Project 1 (Growth vs. Development)

What each phase taught, what to watch out for, and how to talk about it in interviews.
Phases 0–5 are complete. Phases 6–7 are previews and get filled in as each one is finished.

**How to use this:** before an interview, read the "Interview questions" for each phase out loud and answer in your own words before reading the sample answer. If you can't explain something without looking, that's the part to revisit.

---

## Contents

- [Phase 0: Setup](#phase-0-setup)
- [Phase 1: Exploring the source](#phase-1-exploring-the-source)
- [Phase 2: Ingestion](#phase-2-ingestion)
- [Phase 3: dbt sources and staging](#phase-3-dbt-sources-and-staging)
- [Phase 4: Intermediate and mart models](#phase-4-intermediate-and-mart-models)
- [Phase 5: Tests and documentation](#phase-5-tests-and-documentation)
- [Phase 6: Analysis notebook (preview)](#phase-6-analysis-notebook-preview)
- [Phase 7: README and demo (preview)](#phase-7-readme-and-demo-preview)
- [Glossary](#glossary)

---

## Phase 0: Setup

**In one sentence:** before writing any pipeline code, set up an environment that anyone can recreate and that keeps secrets out of git.

### Key concepts

| Concept | What it means | Where it is in this project |
| --- | --- | --- |
| Virtual environment | A private folder of Python packages for one project, so projects don't break each other | `.venv/` (activate with `source .venv/bin/activate`) |
| Pinned dependencies | Recording the exact version of every package, so the project installs the same way on any machine | `requirements.txt` (made with `pip freeze`) |
| `.gitignore` | A list of files git must never track: secrets, build output, the virtual environment | `growth_vs_econdev/.gitignore` |
| Cloud project | A container in Google Cloud that holds resources and billing | `econdev-portfolio-alice` |
| Dataset (BigQuery) | A folder of tables. Each layer gets its own | `raw` (ingestion output), `dbt_dev` (dbt output) |
| Dataset location | The region where data is stored. Datasets that are queried together must share a location | Both are in `US` |
| Two kinds of login | `gcloud auth login` logs in the command-line tool; `gcloud auth application-default login` gives your *code* credentials (ADC) | Python, dbt and Jupyter all use ADC |
| Jupyter kernel | The Python environment a notebook runs in | `Python (econdev)` points at `.venv` |
| Feature branch | A separate line of work in git, merged into `main` when ready | `alice_econdev` |

### What to watch out for

- **Never commit credentials.** No service-account key files in the repo. Use `gcloud` login locally; real production systems use a secrets manager.
- **Wrong environment.** If a notebook or terminal uses a different Python, you'll get "module not found" errors or different package versions. Check for `(.venv)` in your prompt and `Python (econdev)` in Jupyter.
- **Location mismatch.** A dataset in `EU` and another in `US` can't be joined in one query.
- **Unpinned versions.** "It works on my machine" usually means different package versions.

### Real problems we hit (good interview stories)

1. **SSL certificate errors on install.** Python from python.org on macOS doesn't trust HTTPS certificates until you run `Install Certificates.command`. Fixed by pointing the install at a certificate bundle.
2. **A package wouldn't install on an Intel Mac.** The newest `cryptography` release had no pre-built version for Intel Macs, so pip tried to compile it and failed. Fixed by telling pip to prefer pre-built versions (`--prefer-binary`) and pinning the result in `requirements.txt`.

> Interviewers love "tell me about a time something broke." Environment problems are real engineering work: diagnosing them shows you read error messages instead of guessing.

### Interview questions

**Q: How do you make sure someone else can run your project?**
A: Everything runs in a virtual environment with pinned versions in `requirements.txt`, configuration lives in a YAML file rather than in code, and the README lists the exact setup steps. Credentials come from each person's own Google login, so nothing secret is shared.

**Q: How do you handle credentials?**
A: They never touch the repo. Locally I use Application Default Credentials from `gcloud`. The `.gitignore` blocks key files and `.env` files as a second safety net.

---

## Phase 1: Exploring the source

**In one sentence:** look at the real data before designing anything, because the source's quirks decide your design.

### Key concepts

| Concept | What it means | What we found |
| --- | --- | --- |
| Data profiling | Systematically checking a new dataset: shape, types, nulls, ranges, coverage | Done in `notebooks/exploratory.ipynb` |
| API response shape | How the source packages its data | World Bank returns a 2-item list: `[page metadata, records]` |
| Grain | What one row represents. Decide it before writing any SQL | One country, one indicator, one year |
| Nested fields | Values inside other values | `indicator.id`, `country.value` need extracting |
| Types | Whether a value is text, a number, a date | `date` arrives as text (`"2025"`) and must be cast |
| Identifiers | Codes that identify things. Pick one and use it everywhere | 3-letter `countryiso3code` (not the 2-letter `country.id`) |
| Coverage | How many expected values actually exist | GDP, unemployment: 26 of 26 years. Mobile: 25. Poverty: 3 to 6 |
| Null vs zero | Null means "unknown / not measured"; zero is a real value | Poverty nulls mean "no survey that year", not "zero poverty" |

### Two different kinds of missing data

This distinction is subtle and impressive to explain:

| Kind | Example | Cause | How to handle |
| --- | --- | --- | --- |
| **Structural gaps** | Poverty: only 3 to 6 values in 26 years | Measured by household surveys every few years | Keep nulls; compare between survey years; never pretend the gaps are real data |
| **Publication lag** | Mobile: missing only 2025 | The newest year isn't published yet | Expected; will fill in on a future run |

### Forward-filling: useful, but dangerous in the warehouse

Forward-filling means repeating the last known value until a new one appears (for example, using Kenya's 2015 poverty rate for 2016 to 2019).

- **The risk:** once filled in the warehouse, nobody can tell a measured value from a guess.
- **Our approach:** the mart keeps nulls plus a `poverty_survey_year` column. If a chart needs a value every year, the notebook fills it and labels it as carried forward.

### What to watch out for

- **Assuming the data is complete.** Always build a coverage table (count non-null values per group).
- **Treating null as zero.** That turns "unknown" into "nothing", which silently changes averages and trends.
- **Indicator definitions change.** The World Bank moved its poverty line from $2.15 to $3.00 a day (2021 prices) in 2025, so older articles quote different numbers.

### Interview questions

**Q: What's the first thing you do with a new data source?**
A: Profile it before building anything: look at the raw response, identify the grain, check types, and build a coverage table of how many values actually exist. In this project that showed poverty data only exists for 3 to 6 survey years per country, which shaped the whole analysis design.

**Q: How did you handle missing data?**
A: I separated two causes. Poverty has structural gaps because it comes from occasional surveys, so I keep nulls and compare change between survey years instead of year by year. Mobile is only missing the latest year because of publication lag, which is expected. I avoided forward-filling in the warehouse because it hides which values were actually measured.

**Q: What's the grain of your data?**
A: In staging, one row per country, indicator and year. In the final mart, one row per country and year, with one column per indicator.

---

## Phase 2: Ingestion

**In one sentence:** move the data from the API into BigQuery unchanged, reliably, and safely rerunnable.

### Where it fits: the "EL" of ELT

- **ETL** (older): extract, transform in Python, then load the cleaned result.
- **ELT** (modern): extract, load the raw data, then transform inside the warehouse with SQL (dbt).
- **Why ELT:** raw data is kept, so a buggy transformation can be fixed and rebuilt without re-fetching. Transformations are SQL in version control: easy to test and review.

Your ingestion is deliberately "dumb": it does no cleaning, renaming or calculation.

### The code, in plain English

| File | What it does |
| --- | --- |
| `config/indicators.yml` | Lists countries, years, indicators and the destination table |
| `ingestion/worldbank_client.py` | `fetch_page`: one API request, with retries. `fetch_indicator`: loops over all pages |
| `ingestion/ingest.py` | Fetches every indicator, turns records into rows, checks the row count, loads into BigQuery |
| `tests/test_ingestion.py` | Checks the paging loop and row-building with fake data |

Run it with `python -m ingestion.ingest`. Test it with `python -m pytest tests -v`.

### Key concepts

**1. Pagination.** APIs return data in pages. The loop requests page 1, 2, 3… until `page == pages`.
Watch out: forgetting to page raises no error. You silently load only page 1.

**2. Retries with exponential backoff.** On a network failure, wait and try again with growing pauses (2s, then 4s).
- *Transient errors* (timeouts, dropped connections, 5xx server errors): retry; they often succeed next time.
- *Permanent errors* (4xx, such as a bad indicator code): fail immediately; asking again won't help.
- *Timeouts:* every request has a 30-second limit, so a hung connection can't freeze the pipeline.
- Real example: during testing, the World Bank API dropped the connection twice and the retries recovered automatically.

**3. Raw layer design.** Each row stores:
- `payload`: the complete original record as JSON text. Nothing is lost.
- `indicator_id`, `country_iso3`, `year`: copied out for easy filtering, still as text (staging casts types).
- `ingested_at`: when *our pipeline* loaded it.
- `source_last_updated`: when *the World Bank* last revised the indicator.

The last two are metadata. They answer "how fresh is this?" and "did the source change?"

**4. Idempotency.** Running the pipeline twice gives the same result as running it once.
- We use `WRITE_TRUNCATE`: replace the table's contents each run. Verified: two runs, still 520 unique rows.
- `WRITE_APPEND` would duplicate everything on every rerun.
- Trade-off: we keep only the latest snapshot, not a history. Fine here because the World Bank keeps history. The alternative is appending with a run id and keeping only the latest run in staging.

**5. Validate before loading.** The script checks it built exactly 520 rows (5 countries × 4 indicators × 26 years) before touching BigQuery, and stops without loading if not.
Principle: a pipeline that fails loudly gets fixed; one that loads half the data quietly produces wrong dashboards nobody notices.

**6. Configuration over hard-coding.** Changing scope (add a country, change years) is a config edit, not a code change. Project 2 reuses the same client with different indicators.

**7. Testing with fakes (mocking).** Tests replace the real API call with a fake that returns made-up pages.
- Fast (about 1 second), free (no API or BigQuery), repeatable (same answer every time).
- They test *our logic* (are pages combined correctly?), not whether the internet works.
- `assert` lines state what must be true; any failed assert or crash fails the test.
- Passing tests prove the cases they check, not everything. That's why we also ran the real load and queried the result.

**8. Observability.** Logs record counts per indicator, including nulls (`104 with null value` for poverty). If that number changes unexpectedly, the source changed.

### What to watch out for

| Risk | How the pipeline handles it |
| --- | --- |
| Missing pages | Paging loop + a test with 3 fake pages |
| Network blips | Retries with backoff + timeouts |
| Duplicates on rerun | `WRITE_TRUNCATE` (idempotent) |
| Partial or broken loads | Row-count check before loading |
| Buggy transformations | Raw data kept unchanged, so you can rebuild |
| Source revisions | `source_last_updated` recorded |
| Leaked credentials | `gcloud` login, `.gitignore`, no keys in code |
| Silent data changes | Null counts in logs (dbt tests come in Phase 5) |

### Interview questions

**Q: Walk me through your ingestion.**
A: A Python script reads the indicator list from config, calls the World Bank API for each one, following pagination and retrying transient errors with backoff. Each record is stored unchanged as JSON with a few key columns and load metadata. Before loading, it checks the row count matches what's expected, then loads to a BigQuery raw table with a truncate-and-replace so reruns don't duplicate.

**Q: What happens if your pipeline runs twice?**
A: Nothing bad. The load replaces the table instead of appending, so it's idempotent. I verified it: two runs, still 520 unique rows.

**Q: What if the API is down or slow?**
A: Transient failures are retried up to three times with exponential backoff, and every request has a timeout. If it still fails, the script raises an error and loads nothing, so there's never partial data in the warehouse.

**Q: Why store raw JSON instead of a clean table?**
A: So transformations can be fixed and rebuilt without re-fetching, and so there's an untouched record of exactly what the source sent. It also means a new field the source adds later is already captured.

**Q: Why WRITE_TRUNCATE and not incremental loads?**
A: The whole dataset is 520 rows, so a full refresh is simple, cheap and always consistent. I'd switch to incremental loads if the data were large or if I needed to keep a history of source revisions.

**Q: How did you test it?**
A: Unit tests with a fake API cover the paging logic and row building, so they're fast and don't depend on the network. Then an end-to-end run, run twice, confirmed the row count and that there were no duplicates.

---

## Phase 3: dbt sources and staging

**In one sentence:** dbt takes over from Python: it reads the raw table as a declared *source* and builds a clean, typed staging model, all as version-controlled SQL.

### What dbt actually is

dbt doesn't move data and doesn't store it. It's a tool that **runs your SQL `select` statements inside the warehouse and saves the results as views or tables**, in the right order. What it adds on top of plain SQL:
- **Dependencies:** `source()` and `ref()` tell dbt which models depend on which, so it builds them in order and draws the lineage graph.
- **Tests and docs** in YAML next to the models (Phase 5).
- **Environments:** the same code can build into a dev dataset or a production one.

### The files, in plain English

| File | What it does |
| --- | --- |
| `econdev_dbt/dbt_project.yml` | Project settings: name, folders, and how each layer is materialised |
| `econdev_dbt/profiles.yml` | How to connect to BigQuery (`method: oauth` = your gcloud login; no secrets, safe to commit) |
| `models/staging/_worldbank__sources.yml` | Declares the raw table as a source, with a freshness check |
| `models/staging/stg_worldbank__indicators.sql` | The staging model: casts types, pulls fields out of the JSON |
| `models/staging/_worldbank__models.yml` | Describes the staging model and every column |

Run from inside `econdev_dbt/`: `dbt debug` (test connection), `dbt build --select staging` (build + test), `dbt source freshness`.

### Key concepts

**1. Sources vs refs.** `{{ source('worldbank', 'worldbank_indicators') }}` points at a table dbt did *not* build (ingestion loaded it). `{{ ref('model_name') }}` points at a model dbt *did* build. Never hard-code table names: these functions are how dbt knows the build order and draws lineage.

**2. Source freshness.** `loaded_at_field: ingested_at` plus `warn_after: 35 days` / `error_after: 60 days`. `dbt source freshness` checks how old the newest `ingested_at` is. It catches the silent failure where ingestion stops running and everything downstream quietly goes stale.

**3. Staging conventions.** One staging model per source table, and staging only does:
- **Cast types:** `year` text to `INT64`; `value` to `FLOAT64`; `source_last_updated` text to `DATE`.
- **Extract:** `JSON_VALUE(payload, '$.country.value')` is the SQL version of `record["country"]["value"]`.
- **Rename** to clear, consistent names (`indicator_name` like `gdp_growth_pct`).
- **No filtering and no business logic.** Nulls stay. Any decisions about the data happen in later layers, where they're visible.

**4. CTE structure.** The model is written as `with source as (...), renamed as (...) select * from renamed`. Each CTE (common table expression) is one named step, so the SQL reads top to bottom like a recipe. This is the standard dbt style.

**5. Materialisation.** Staging is a **view**: a saved query that always shows the latest raw data and uses no storage. Marts will be **tables**: stored results, fast to query. Set per folder in `dbt_project.yml`.

**6. `cast` vs `safe_cast`.** We use `cast`, which **fails** if a value can't be converted. `safe_cast` would quietly turn bad values into null. In staging you want loud failures, so a source format change gets noticed instead of becoming mysterious nulls.

**7. Verify, don't assume.** After building, we queried the model: 520 rows, 520 unique grain combinations, years 2000 to 2025, every indicator mapped, 109 nulls (matching the ingestion logs). Then we investigated a surprising value (below).

### A real data surprise: mobile subscriptions of 0.02

The minimum `mobile_per_100` looked like 0.0. Investigating showed Nigeria at 0.02 subscriptions per 100 people in 2000, because Nigeria's GSM networks launched in 2001. Real history, not a bug. The habit: **when a value looks wrong, query the rows behind it before deciding**.

### What to watch out for

| Risk | What happens | How we guard against it |
| --- | --- | --- |
| Hard-coded table names | dbt can't see dependencies; lineage breaks | Always `source()` / `ref()` |
| Silent type failures | Bad values turn into nulls unnoticed | `cast`, not `safe_cast`, in staging |
| Business logic in staging | Decisions get buried where nobody looks | Staging only casts, extracts, renames |
| Stale data | Pipeline stopped, dashboards look fine | Source freshness check |
| Location mismatch | "Dataset not found in location" errors | Profile `location: US` matches the datasets |
| New indicator added to config | `indicator_name` comes out null | Phase 5 test: `indicator_name` not null |
| Credentials in profiles | Leaked secrets | `method: oauth`; profile holds no secrets |

### Interview questions

**Q: What does dbt do in your pipeline?**
A: dbt handles everything after the raw load. It reads the raw table as a declared source, then builds staging, intermediate and mart models in BigQuery as SQL `select` statements. It works out the build order from `source()` and `ref()`, runs tests, and generates documentation and a lineage graph.

**Q: What's the difference between `source()` and `ref()`?**
A: `source()` points at a table something else loaded, here the raw table from my Python ingestion. `ref()` points at another dbt model. Both replace hard-coded table names so dbt knows the dependencies.

**Q: What goes in a staging model, and what doesn't?**
A: Only light cleaning: casting types, extracting fields from the JSON, and renaming. No filtering, joins or business logic. That keeps staging a reliable, one-to-one cleaned copy of the source, and puts real decisions in later layers where they're visible and tested.

**Q: Why are your staging models views and your marts tables?**
A: Views are saved queries: always up to date and no storage cost, which suits a thin cleaning layer. Marts are what people query repeatedly, so storing them as tables makes queries fast and consistent.

**Q: How would you know if your ingestion stopped running?**
A: A dbt source freshness check on `ingested_at` warns after 35 days and errors after 60. Once orchestration runs it on a schedule, a stalled pipeline gets flagged instead of silently going stale.

**Q: Why `cast` instead of `safe_cast`?**
A: `cast` fails loudly if the source sends something unexpected. `safe_cast` would turn it into a null, and I'd end up with missing data that looks like a real gap. In staging I'd rather the build break.

### Must-know checklist

You should be able to explain each of these in a sentence or two without notes:
- [ ] What dbt does and doesn't do: it runs SQL in the warehouse; it doesn't move or store data itself
- [ ] `source()` vs `ref()`, and why hard-coded table names break lineage
- [ ] What a source freshness check catches
- [ ] The three staging jobs (cast, extract, rename) and the three things staging must *not* do (filter, join, apply business logic)
- [ ] View vs table, and which layer uses which
- [ ] `cast` vs `safe_cast`
- [ ] Why the raw layer keeps the whole JSON payload, and staging parses it
- [ ] The grain of the staging model (one row per country, indicator and year)

### More concept questions (likely follow-ups)

**Q: What's the difference between `dbt run`, `dbt test` and `dbt build`?**
A: `run` builds the models. `test` runs the tests against what's already built. `build` does both, in dependency order, and skips a model's downstream models if its tests fail, so bad data doesn't flow further. I use `build`.

**Q: What does dbt actually send to BigQuery?**
A: Plain SQL. dbt first *compiles* the model: it replaces the Jinja (`{{ ref(...) }}`, `{{ source(...) }}`) with real table names and wraps the `select` in a `create view` or `create table` statement. You can see the compiled SQL in `target/compiled/`, which is the first place to look when debugging.

**Q: What materialisations exist besides view and table?**
A: *Incremental*: only processes new or changed rows on each run, for large tables where a full rebuild is too slow or expensive. *Ephemeral*: not built at all; dbt inlines it as a CTE into the models that use it. My data is small, so views and tables are the simplest correct choice. I'd move a big fact table to incremental if it grew to millions of rows.

**Q: Why store the raw JSON and parse it in dbt, instead of parsing in Python?**
A: If I parse during ingestion and get it wrong, or need a field I didn't extract, I have to re-call the API. With the full payload in raw, I can fix or extend parsing in SQL and rebuild, with no re-ingestion. It also keeps a faithful record of exactly what the source sent.

**Q: What are dev and prod targets?**
A: `profiles.yml` can define several targets pointing at different datasets. I build into `dbt_dev` while developing; a production run would use a `prod` target, so experiments never overwrite what people are using. Same code, different destination.

**Q: Why CTEs instead of nested subqueries?**
A: Each CTE is a named step, read top to bottom, so the logic is easy to follow and review. Nested subqueries are read inside out. BigQuery optimises both the same way, so readability wins.

**Q: The source changes a column format overnight. What happens in your pipeline?**
A: Ingestion still loads it, because raw stores the payload as text. The staging `cast` then fails, so `dbt build` fails *before* anything downstream gets wrong numbers. I'd see the error, look at the raw rows, and update the staging model.

### Explain-back: polished version

> "dbt picks up after ingestion. I declare the raw table as a source with a freshness check, so I'd know if loading stopped. The staging model is a one-to-one cleaned copy of raw: it casts types, extracts fields from the JSON and renames them, at one row per country, indicator and year. It does no filtering, so no data is dropped before anyone can see it. Staging is a view because it's thin and should always reflect raw; marts are tables because they're queried repeatedly. Models reference each other with `ref()`, which is how dbt knows the build order."

## Phase 4: Intermediate and mart models

**In one sentence:** reshape the clean data into tables shaped for the question, changing the grain deliberately and checking that nothing was lost along the way.

### The models and their grain

| Model | Layer | Grain (one row per…) | Rows | Built as |
| --- | --- | --- | --- | --- |
| `stg_worldbank__indicators` | Staging | country, indicator, year | 520 | view |
| `int_indicators_pivoted` | Intermediate | country, year (4 indicator columns) | 130 | view |
| `fct_growth_vs_development` | Mart | country, year (+ trends) | 130 | table |
| `fct_poverty_survey_spans` | Mart | country, pair of consecutive surveys | 21 | table |

Every model reads the one before it with `{{ ref(...) }}`, so dbt builds them in order.

### Key concepts

**1. Long vs wide, and pivoting.**
- *Long* (staging): one row per measurement. Easy to load and test, awkward to compare indicators.
- *Wide* (intermediate and marts): one row per country-year, one column per indicator. Easy to compare and chart.
- *How:* conditional aggregation, `max(case when indicator_name = 'gdp_growth_pct' then value end)`, grouped by country and year. The `max` is only there because SQL needs an aggregate; each group has at most one value per indicator. BigQuery also has a `PIVOT` operator; conditional aggregation works in every SQL dialect.

**2. Grain changes are the riskiest step.** Every change of grain can lose or duplicate data. We checked: non-null counts were identical in staging, intermediate and mart (130 / 26 / 125 / 130), and both marts have zero duplicate keys.

**3. Why an intermediate layer?** The pivot is reused by both marts. Doing it once, in its own model, means one place to fix and test it. Intermediate models are building blocks, not things people query directly.

**4. Window functions** (calculations across related rows, without collapsing them like `group by` does):
- `lag(x) over (partition by country order by year)`: the previous year's value, used for year-on-year change.
- `avg(x) over (… rows between 4 preceding and current row)`: a 5-year rolling average.
- `partition by` keeps each country separate; `order by` sets the sequence; a named `window` clause avoids repeating the definition.
- Guard against misleading early values: the rolling average is only filled once 5 years exist.

**5. Filtering belongs in the right layer.** `fct_poverty_survey_spans` filters to survey years. That's a deliberate analysis decision, so it lives in a mart (documented) and not in staging (where it would be hidden). This is the explain-back question from Phase 3 in practice.

**6. Design the table around what the data can support.** Poverty exists only in survey years, so year-by-year comparisons with GDP are meaningless. The spans mart compares *change between two surveys* with *growth over the same years*. That's the honest grain for the business question.

**7. Compounding.** Growth of 5% then 5% is 10.25% in total, not 10%. `exp(sum(ln(1 + g/100))) - 1` multiplies yearly rates in SQL (there's no `product()` aggregate). It's a small detail that shows care.

**8. Fact tables.** Both marts are named `fct_` because each row records measurements (facts) at a stated grain. Country names sit directly on the rows for now; Project 2 splits those into proper dimension tables (`dim_country`, `dim_year`).

### First look at the results

A few spans already tell different stories (to be explored properly in Phase 6):
- **Rwanda 2016 to 2023:** poverty fell 25 percentage points alongside steady growth (55% cumulative): growth looks broad-based.
- **Kenya 2015 to 2020:** the economy grew 20%, yet poverty *rose* 6.7 points: growth not reaching the poorest.
- **Nigeria 2018 to 2022:** almost no growth (0.9%) and poverty rose 7.6 points.
- **South Africa 2014 to 2022:** poverty fell 10.5 points with only 5.5% growth, while unemployment rose 8.4 points: something other than growth drove it (a question to research, not assume).

Caveat: survey methods can change between rounds, so big jumps should be checked against World Bank notes before drawing conclusions.

### What to watch out for

| Risk | What happens | How we guard against it |
| --- | --- | --- |
| Pivot loses values | Indicators silently disappear | Non-null counts compared across layers |
| Join or pivot duplicates rows | Inflated averages and counts | Duplicate-key checks (tests in Phase 5) |
| Filtering the wide table on one indicator | Drops the other indicators for those years | Never filter `fct_growth_vs_development`; spans mart filters deliberately |
| Window without `partition by` | Kenya's previous year becomes Ghana's last year | Always partition by country |
| Rolling average on too few years | Early values look precise but aren't | Only filled when 5 years exist |
| Adding growth rates instead of compounding | Understates total growth | `exp(sum(ln(...)))` |
| Reading correlation as cause | Overstated conclusions | Phase 6 phrases findings carefully |

### Interview questions

**Q: Walk me through your model layers.**
A: Staging is one row per country, indicator and year: cleaned and typed. An intermediate model pivots that to one row per country-year with a column per indicator. Two marts build on it: a country-year fact table with trends like a 5-year rolling growth average, and a survey-span table that compares poverty change between consecutive surveys with GDP growth over the same years.

**Q: How do you make sure a transformation doesn't lose data?**
A: I state the grain of every model and check it. For the pivot I compared non-null counts per indicator across staging, intermediate and mart, and checked the marts have no duplicate keys. In Phase 5 those checks become automated dbt tests.

**Q: Why did you build the survey-span table?**
A: Poverty is only measured every few years, so comparing it with GDP year by year would mean comparing against mostly empty values or invented ones. The span table matches each poverty change with growth over exactly the same years, which is the comparison the data actually supports.

**Q: What's a window function and where did you use one?**
A: A calculation across related rows that keeps every row, unlike `group by`. I used `lag` for year-on-year changes and a 5-year rolling average of GDP growth, both partitioned by country so countries never mix.

**Q: Why an intermediate model rather than pivoting inside each mart?**
A: Both marts need the same pivot. Doing it once means one definition to test and fix, and the marts stay focused on their own logic.

### Must-know checklist

- [ ] The grain of every model (see the table at the top of this phase), and how it changes at each step
- [ ] Long vs wide, and how conditional aggregation pivots one into the other
- [ ] How to check a grain change didn't lose or duplicate rows
- [ ] Window function vs `group by`
- [ ] `lag`, rolling averages, `partition by`, `order by` and the window frame (`rows between …`)
- [ ] Why the spans mart exists (poverty is measured only every few years)
- [ ] Why filtering happens in the mart, not in staging
- [ ] Compounding vs adding growth rates
- [ ] Percent vs percentage points
- [ ] What a fact table is, and what a dimension table would add

### More concept questions (likely follow-ups)

**Q: What is "grain", and why do you keep talking about it?**
A: The grain is what one row represents, for example "one country in one year". Every other decision depends on it: what joins are safe, what can be summed, and what the unique key is. Most data bugs are grain bugs: a join that turns one row into three, or a pivot that silently drops values.

**Q: Window function vs `group by`?**
A: `group by` collapses rows: 26 years become one row per country. A window function computes across related rows but keeps every row, so each year gets its own rolling average or previous-year value.

**Q: What does `lag` return for a country's first year?**
A: Null, because there's no previous row in that partition. That's correct: the 2000 year-on-year change is genuinely unknown, and it shouldn't be treated as zero.

**Q: How does `avg` treat nulls, and why does it matter here?**
A: `avg` ignores nulls. So a "5-year" average over a window with two missing years is really a 3-year average, which looks just as precise. That's why the rolling average is only filled when `count(gdp_growth_pct)` over the window equals 5.

**Q: `rows between` vs `range between`?**
A: `rows` counts physical rows: "the 4 rows before this one". `range` uses the values in the `order by` column: "years within 4 of this one". With exactly one row per country-year they give the same answer. If years could be missing, `range` would be the safer way to say "last 5 calendar years".

**Q: A join suddenly doubled your row count. How do you debug it?**
A: That's a fan-out: the join key isn't unique on one side. I check the grain of each input by grouping by the join key and looking for counts above 1, then fix the key or deduplicate before joining. A unique-combination test on each model's grain catches this automatically.

**Q: In the spans mart, why an inner join for growth but left joins for unemployment?**
A: Every span must have growth years, or the row is meaningless, so an inner join is correct. Unemployment is extra context; a left join keeps the span even if unemployment were missing for one of the years.

**Q: Percent vs percentage points?**
A: Poverty going from 40% to 30% is a fall of 10 *percentage points*, but a 25 *percent* fall relative to where it started. I report poverty change in percentage points (the `_pp` suffix) so there's no ambiguity.

**Q: Why not use BigQuery's `PIVOT` operator?**
A: It works, but conditional aggregation runs in every SQL dialect and makes each column's logic explicit. Either is fine; I'd mention I know both.

**Q: What's a fact table, and what would a dimension table add?**
A: A fact table holds measurements at a stated grain, here indicator values per country-year. A dimension table holds descriptive attributes for things you filter and group by, for example `dim_country` with region and income group. Facts join to dimensions by key, which is a star schema. I'll add dimensions in Project 2.

**Q: Your mart shows Kenya's economy grew while poverty rose. Does growth cause poverty?**
A: No. The table shows the two moved in opposite directions over the same years; it doesn't show why. Possible explanations include where the growth happened, population growth, or changes in survey methods. I present it as a question worth investigating, not a conclusion.

### Explain-back: polished version

> "The raw data is long, one row per country, indicator and year. I pivoted it to one row per country and year, so every indicator for a year sits side by side, and I checked the non-null counts matched before and after. Poverty is only surveyed every few years, so I built a second mart at a different grain, one row per country per pair of back-to-back surveys. It compares how much poverty changed between two surveys with how much the economy grew over those same years, with unemployment as extra context."

## Phase 5: Tests and documentation

**In one sentence:** turn every check we did by hand into automated dbt tests that run on each build, and generate a documentation site that explains the project to anyone.

### What we added

| File | What it does |
| --- | --- |
| `econdev_dbt/packages.yml` | Installs `dbt_utils` (ready-made tests). Run `dbt deps` once after cloning |
| `econdev_dbt/package-lock.yml` | Pins the exact package version (1.4.1), so everyone installs the same one |
| Tests in each `_*.yml` file | 39 generic tests on the source, staging, intermediate and marts |
| `econdev_dbt/tests/assert_pivot_keeps_every_value.sql` | A custom test: the pivot must not lose any values |
| `econdev_dbt/models/overview.md` | The front page of the docs site |

Commands, from inside `econdev_dbt/`: `dbt build` (build and test everything), `dbt test` (tests only), `dbt docs generate` then `dbt docs serve` (opens the docs site in your browser; Ctrl+C to stop).

### Key concepts

**1. Two kinds of dbt test.**
- *Generic tests* are reusable and declared in YAML against a column or model: `not_null`, `unique`, `accepted_values`, `relationships`, plus package tests like `dbt_utils.unique_combination_of_columns`.
- *Singular tests* are one-off SQL files in `tests/`. The rule for both: **a test is a query that returns the bad rows; it passes when it returns nothing.**

**2. What each test protects against.**

| Test | Where | Catches |
| --- | --- | --- |
| `unique_combination_of_columns` | Every layer | Grain bugs: double loads, join fan-out, a broken pivot |
| `not_null` | Keys and required columns | Missing keys, broken JSON extraction |
| `accepted_values` (countries, indicator names) | Source, staging | Unexpected countries; an indicator added to config but not mapped in staging |
| `accepted_range` (0–100 for percentages) | Intermediate | Units or parsing bugs, e.g. a value of 4000% |
| `equal_rowcount` | `fct_growth_vs_development` | The mart adding or dropping rows |
| `expression_is_true` (`end_year > start_year`) | Spans mart | Broken `lag` logic |
| `relationships` | Spans mart | A span for a country that doesn't exist in the main mart |
| `assert_pivot_keeps_every_value` | Custom | The pivot silently losing values |

**3. Test the source too.** Tests on the raw table catch problems at the door (double loads, unexpected countries) before any model is built on them.

**4. Severity: error vs warn.** Most tests fail the build. The GDP growth range (−30% to +30%) only *warns*, because real growth can be extreme (war, pandemic). Use `warn` for "this looks unusual, have a look" and `error` for "this is definitely wrong".

**5. `dbt build` stops bad data spreading.** Tests run straight after each model. If a model's tests fail, everything downstream is **skipped**, so the marts keep their last good version instead of being rebuilt from bad data.

**6. See a test fail before trusting it.** We deliberately broke the pivot (mislabelled poverty). The custom test failed, and `dbt build` skipped both marts. A test you've never seen fail might not be testing anything.

**7. Documentation is generated from what you already wrote.** `dbt docs generate` combines the YAML descriptions, the SQL, the tests and the column types from BigQuery into a website with a **lineage graph**. Descriptions are written once, next to the code, so they stay up to date.

**8. Packages and lock files.** `packages.yml` says which packages you want; `package-lock.yml` records the exact version installed. Commit both; never commit `dbt_packages/` (it's re-downloadable, like `.venv/`).

### What to watch out for

| Risk | What happens | How we guard against it |
| --- | --- | --- |
| Tests that never fail | False confidence | Broke the pivot on purpose and watched the test catch it |
| Too many warnings | People learn to ignore them | `warn` only where unusual values are genuinely possible |
| Testing only the marts | Problems found late and hard to trace | Tests at every layer, starting with the source |
| `unique` on one column when the grain is several | Test can't express the real grain | `unique_combination_of_columns` |
| Hard-coded expected values (e.g. 5 countries) | Test fails when scope changes on purpose | Update the test with the config; that failure is a useful reminder |
| Range tests too tight or too loose | Noise, or bugs slip through | Ranges based on what's physically possible (0–100%) |
| Old test syntax | Deprecation warnings in dbt 1.10+ | Test parameters go under `arguments:` |

### Interview questions

**Q: How do you test your dbt models?**
A: At every layer. The source has grain, not-null and accepted-values tests, so bad loads are caught at the door. Each model has a unique-combination test on its grain, range tests on percentages, and a row-count test where a model shouldn't change the number of rows. I also wrote a custom test that checks the pivot keeps every value. 40 tests run on every `dbt build`.

**Q: What's the difference between a generic and a singular test?**
A: A generic test is reusable and configured in YAML, like `not_null` or `unique`. A singular test is a one-off SQL query in the `tests/` folder for logic specific to my project. Both work the same way: the query returns failing rows, and zero rows means pass.

**Q: What's the single most important test?**
A: A uniqueness test on each model's grain. Most serious data bugs, like duplicate loads or join fan-out, show up as broken grain, and they silently inflate every sum and average downstream.

**Q: What happens when a test fails?**
A: With `dbt build`, the failing model's downstream models are skipped, so bad data doesn't reach the marts and they keep their last good version. I tested this by breaking the pivot on purpose: the custom test failed and both marts were skipped.

**Q: When would you use `severity: warn`?**
A: When an unusual value could still be real. GDP growth outside ±30% is rare but possible, so it warns for a human to check rather than blocking the pipeline. A percentage over 100 is impossible, so that fails.

**Q: How do you document your project?**
A: Descriptions for every model and column live in YAML next to the SQL, plus an overview page. `dbt docs generate` turns them into a website with column types and a lineage graph, so a new person can see what each table is, its grain, and where it comes from.

### Must-know checklist

- [ ] A dbt test is a query returning bad rows; zero rows = pass
- [ ] Generic vs singular tests
- [ ] Which test protects the grain, and why it matters most
- [ ] What `dbt build` does when a test fails (skips downstream)
- [ ] Error vs warn severity, with an example of each
- [ ] Why test the source, not just the marts
- [ ] What the docs site shows and where its content comes from
- [ ] `packages.yml` vs `package-lock.yml` vs `dbt_packages/`

### Explain-back prompt

In a few sentences: what does a dbt test actually do, which test you'd keep if you could only have one (and why), and what happened when we broke the pivot.

## Phase 6: Analysis notebook (preview)

- **Reading only from the mart**, never raw tables.
- **Correlation vs causation:** say "moved together", not "caused".
- **Stating limitations:** sparse poverty data, modeled unemployment estimates.

## Phase 7: README and demo (preview)

- **Telling the story:** question, architecture, how to run, findings, limitations.
- **A 5-minute walkthrough:** trace one number from the final chart back to the raw API record.

---

## Glossary

| Term | Meaning |
| --- | --- |
| ADC | Application Default Credentials: the Google login your code uses |
| API | A web address that returns data instead of a web page |
| Backoff | Waiting longer between each retry |
| Bronze / raw layer | Data exactly as the source sent it |
| CTE | Common table expression: a named step in a SQL query (`with name as (...)`) |
| Freshness | How old the newest data is; dbt can warn when it gets too old |
| Lineage | The map of which tables feed which; dbt draws it from `source()` and `ref()` |
| Long vs wide | Long: one row per measurement. Wide: one row per entity-period, one column per measure |
| Package | Reusable dbt code from the community, e.g. `dbt_utils` |
| Pivot | Turning long data into wide data |
| Percentage points (pp) | The difference between two percentages: 40% to 35% is −5 pp (a 12.5% relative fall) |
| Window function | A calculation across related rows that keeps every row (`lag`, rolling `avg`) |
| ELT | Extract, Load, then Transform inside the warehouse |
| Grain | What one row represents |
| Idempotent | Running it twice gives the same result as once |
| Kernel | The Python environment a notebook runs in |
| Generic test | A reusable dbt test declared in YAML (`not_null`, `unique`, …) |
| Mart | Final, analysis-ready table |
| Materialisation | How dbt builds a model: view, table, incremental |
| Metadata | Data about data (when loaded, when revised) |
| Mocking | Replacing a real dependency with a fake in tests |
| Pagination | Splitting a large API result across numbered pages |
| Severity | Whether a failing test errors (stops the build) or only warns |
| Singular test | A one-off SQL test in `tests/`; returns the failing rows |
| `ref()` | dbt function that points at another dbt model |
| `source()` | dbt function that points at a table dbt didn't build (e.g. the raw table) |
| Staging | Cleaned, typed, renamed copy of a source table |
| Transient error | A temporary failure that may succeed on retry |
| `WRITE_TRUNCATE` | BigQuery load mode that replaces the table's contents |
