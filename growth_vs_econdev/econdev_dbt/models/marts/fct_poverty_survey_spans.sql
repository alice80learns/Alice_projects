-- Mart: one row per country per pair of consecutive poverty surveys.
-- Answers the business question at the only grain the poverty data supports:
-- "between two surveys, how much did the economy grow, and how did poverty change?"
--
-- This is the layer where we DO filter to survey years: it's a deliberate,
-- documented analysis decision, which is why it lives here and not in staging.

with pivoted as (

    select * from {{ ref('int_indicators_pivoted') }}

),

surveys as (

    select country_iso3, country_name, year as survey_year, poverty_pct
    from pivoted
    where poverty_pct is not null

),

-- pair each survey with the one before it (lag = "previous row")
spans as (

    select
        country_iso3,
        country_name,
        lag(survey_year) over by_survey as start_year,
        survey_year as end_year,
        lag(poverty_pct) over by_survey as poverty_start_pct,
        poverty_pct as poverty_end_pct
    from surveys
    window by_survey as (partition by country_iso3 order by survey_year)

),

-- growth during each span: the years after the start survey up to the end survey
growth_in_span as (

    select
        spans.country_iso3,
        spans.start_year,
        avg(pivoted.gdp_growth_pct) as avg_gdp_growth_pct,
        -- compounding: 5% then 5% is 10.25% total, not 10%. exp(sum(ln(...))) multiplies the yearly rates.
        (exp(sum(ln(1 + pivoted.gdp_growth_pct / 100))) - 1) * 100 as cumulative_gdp_growth_pct
    from spans
    inner join pivoted
        on pivoted.country_iso3 = spans.country_iso3
        and pivoted.year > spans.start_year
        and pivoted.year <= spans.end_year
    group by spans.country_iso3, spans.start_year

),

final as (

    select
        spans.country_iso3,
        spans.country_name,
        spans.start_year,
        spans.end_year,
        spans.end_year - spans.start_year as span_years,

        spans.poverty_start_pct,
        spans.poverty_end_pct,
        spans.poverty_end_pct - spans.poverty_start_pct as poverty_change_pp,

        growth_in_span.avg_gdp_growth_pct,
        growth_in_span.cumulative_gdp_growth_pct,

        start_year_data.unemployment_pct as unemployment_start_pct,
        end_year_data.unemployment_pct as unemployment_end_pct,
        end_year_data.unemployment_pct - start_year_data.unemployment_pct as unemployment_change_pp

    from spans
    inner join growth_in_span
        on growth_in_span.country_iso3 = spans.country_iso3
        and growth_in_span.start_year = spans.start_year
    left join pivoted as start_year_data
        on start_year_data.country_iso3 = spans.country_iso3
        and start_year_data.year = spans.start_year
    left join pivoted as end_year_data
        on end_year_data.country_iso3 = spans.country_iso3
        and end_year_data.year = spans.end_year
    where spans.start_year is not null  -- a country's first survey has no earlier one to pair with

)

select * from final
