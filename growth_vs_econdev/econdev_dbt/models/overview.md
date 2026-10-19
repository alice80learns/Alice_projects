{% docs __overview__ %}
# Growth vs. Development

Does GDP growth translate into broad-based development (less poverty, more jobs,
wider access to mobile services) in Nigeria, Kenya, Ghana, Rwanda and South Africa, 2000–2025?

**Pipeline:** World Bank API → Python ingestion → BigQuery `raw` → dbt (staging → intermediate → marts)

| Layer | Model | One row per… |
| --- | --- | --- |
| Source | `worldbank.worldbank_indicators` | country, indicator, year (raw JSON) |
| Staging | `stg_worldbank__indicators` | country, indicator, year (typed) |
| Intermediate | `int_indicators_pivoted` | country, year |
| Mart | `fct_growth_vs_development` | country, year (+ trends) |
| Mart | `fct_poverty_survey_spans` | country, pair of consecutive poverty surveys |

**Start here:** `fct_poverty_survey_spans` answers the main question, because poverty is
only measured in survey years. Use `fct_growth_vs_development` for year-by-year charts.

Click the blue lineage button (bottom right) to see how the models connect.
{% enddocs %}
