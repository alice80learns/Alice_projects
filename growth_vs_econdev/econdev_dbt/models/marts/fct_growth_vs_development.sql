-- Mart: one row per country and year, with each indicator plus derived trends.
-- Used for year-by-year charts. Poverty stays null in years without a survey;
-- is_poverty_survey_year flags the years with a real measurement.

with pivoted as (

    select * from {{ ref('int_indicators_pivoted') }}

),

final as (

    select
        country_iso3,
        country_name,
        year,

        -- growth
        gdp_growth_pct,
        -- 5-year rolling average smooths out single good or bad years.
        -- Only filled once 5 years of data exist, so early years aren't misleading.
        case
            when count(gdp_growth_pct) over last_5_years = 5
                then avg(gdp_growth_pct) over last_5_years
        end as gdp_growth_5yr_avg,

        -- development
        poverty_pct,
        poverty_pct is not null as is_poverty_survey_year,

        unemployment_pct,
        unemployment_pct - lag(unemployment_pct) over by_year as unemployment_change_pp,

        mobile_per_100,
        mobile_per_100 - lag(mobile_per_100) over by_year as mobile_change_per_100

    from pivoted
    window
        by_year as (partition by country_iso3 order by year),
        last_5_years as (partition by country_iso3 order by year rows between 4 preceding and current row)

)

select * from final
