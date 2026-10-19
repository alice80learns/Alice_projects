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
        max(case when indicator_name = 'unemployment_pct' then value end) as unemployment_pct,
        max(case when indicator_name = 'gdp_per_capita_growth_pct' then value end) as gdp_per_capita_growth_pct,
        max(case when indicator_name = 'vulnerable_employment_pct' then value end) as vulnerable_employment_pct,
        max(case when indicator_name = 'income_share_bottom20_pct' then value end) as income_share_bottom20_pct,
        max(case when indicator_name = 'electricity_access_pct' then value end) as electricity_access_pct,
        max(case when indicator_name = 'life_expectancy_years' then value end) as life_expectancy_years

    from indicators
    group by country_iso3, country_name, year

)

select * from pivoted
