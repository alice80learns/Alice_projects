-- Pivot: from one row per country, indicator and year (long)
--        to one row per country and year, one column per indicator (wide).
--
-- Technique: "conditional aggregation". For each country-year group, each
-- max(case ...) picks out the single value for one indicator. max() is only
-- there because SQL needs an aggregate; each group holds at most one value per
-- indicator. Years without data stay null; no rows are dropped.

with indicators as (

    select * from {{ ref('stg_worldbank__indicators') }}

),

pivoted as (

    select
        country_iso3,
        country_name,
        year,
        max(case when indicator_name = 'gdp_growth_pct' then value end) as gdp_growth_pct,
        max(case when indicator_name = 'poverty_pct' then value end) as poverty_pct,
        max(case when indicator_name = 'mobile_per_100' then value end) as mobile_per_100,
        max(case when indicator_name = 'unemployment_pct' then value end) as unemployment_pct

    from indicators
    group by country_iso3, country_name, year

)

select * from pivoted
