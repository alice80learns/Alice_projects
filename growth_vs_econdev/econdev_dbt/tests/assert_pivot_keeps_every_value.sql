-- Singular test: the long-to-wide pivot must not lose or invent any values.
-- For each indicator, count the non-null values in staging (long) and in the
-- pivoted model (wide). A dbt test passes when its query returns no rows,
-- so this returns only the indicators whose counts differ.

with staging_counts as (

    select indicator_name, count(value) as non_null_values
    from {{ ref('stg_worldbank__indicators') }}
    group by indicator_name

),

pivoted_counts as (

    select 'gdp_growth_pct' as indicator_name, count(gdp_growth_pct) as non_null_values
    from {{ ref('int_indicators_pivoted') }}
    union all
    select 'poverty_pct', count(poverty_pct) from {{ ref('int_indicators_pivoted') }}
    union all
    select 'mobile_per_100', count(mobile_per_100) from {{ ref('int_indicators_pivoted') }}
    union all
    select 'unemployment_pct', count(unemployment_pct) from {{ ref('int_indicators_pivoted') }}

)

select
    coalesce(s.indicator_name, p.indicator_name) as indicator_name,
    s.non_null_values as staging_values,
    p.non_null_values as pivoted_values
from staging_counts as s
full outer join pivoted_counts as p
    on s.indicator_name = p.indicator_name
where s.non_null_values is distinct from p.non_null_values
