-- Staging: one clean, typed row per country, indicator and year.
-- Rules for this layer: rename, cast and extract only. No filtering, no business logic.

with source as (

    select * from {{ source('worldbank', 'worldbank_indicators') }}

),

renamed as (

    select
        -- keys (together they define the grain)
        country_iso3,
        indicator_id,
        cast(year as int64) as year,

        -- readable names, pulled out of the nested JSON
        json_value(payload, '$.country.value') as country_name,
        case indicator_id
            when 'NY.GDP.MKTP.KD.ZG' then 'gdp_growth_pct'
            when 'SI.POV.DDAY' then 'poverty_pct'
            when 'IT.CEL.SETS.P2' then 'mobile_per_100'
            when 'SL.UEM.TOTL.ZS' then 'unemployment_pct'
        end as indicator_name,
        json_value(payload, '$.indicator.value') as indicator_label,

        -- the measurement; null means "no data for that year" and is kept
        cast(json_value(payload, '$.value') as float64) as value,

        -- metadata
        parse_date('%Y-%m-%d', source_last_updated) as source_last_updated,
        ingested_at

    from source

)

select * from renamed
