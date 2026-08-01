/*
Purpose:
Calculate annual gross rental yields by HDB town and flat type.

Method:
1. Calculate the annual median resale price.
2. Calculate the annual median monthly rent.
3. Match rental and resale records by town, flat type and year.
4. Calculate gross rental yield and year-over-year yield changes.

Gross rental yield:
Median monthly rent x 12 / median resale price x 100

Note:
These are unadjusted market-level estimates. Differences in lease age,
street composition and transaction mix may affect comparisons.
*/

WITH annual_resale AS (
    SELECT
        town,
        REPLACE(flat_type, '-', ' ') AS flat_type,
        EXTRACT(YEAR FROM transaction_month)::INTEGER AS year,
        COUNT(*) AS resale_records,
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY resale_price)
            AS median_resale_price
    FROM hdb_resale
    GROUP BY
        town,
        REPLACE(flat_type, '-', ' '),
        EXTRACT(YEAR FROM transaction_month)
),

annual_rental AS (
    SELECT
        town,
        REPLACE(flat_type, '-', ' ') AS flat_type,
        EXTRACT(YEAR FROM approval_month)::INTEGER AS year,
        COUNT(*) AS rental_records,
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY monthly_rent)
            AS median_monthly_rent
    FROM hdb_rental
    GROUP BY
        town,
        REPLACE(flat_type, '-', ' '),
        EXTRACT(YEAR FROM approval_month)
),

annual_yields AS (
    SELECT
        resale.town,
        resale.flat_type,
        resale.year,
        resale.resale_records,
        rental.rental_records,
        resale.median_resale_price,
        rental.median_monthly_rent,
        rental.median_monthly_rent * 12
            / NULLIF(resale.median_resale_price, 0) * 100
            AS gross_rental_yield_pct
    FROM annual_resale AS resale
    INNER JOIN annual_rental AS rental
        ON resale.town = rental.town
        AND resale.flat_type = rental.flat_type
        AND resale.year = rental.year
),

with_previous_year AS (
    SELECT
        *,
        LAG(median_resale_price) OVER (
            PARTITION BY town, flat_type
            ORDER BY year
        ) AS previous_median_resale_price,
        LAG(median_monthly_rent) OVER (
            PARTITION BY town, flat_type
            ORDER BY year
        ) AS previous_median_monthly_rent,
        LAG(gross_rental_yield_pct) OVER (
            PARTITION BY town, flat_type
            ORDER BY year
        ) AS previous_gross_rental_yield_pct
    FROM annual_yields
)

SELECT
    town,
    flat_type,
    year,
    resale_records,
    rental_records,
    ROUND(median_resale_price::NUMERIC, 2)
        AS median_resale_price,
    ROUND(median_monthly_rent::NUMERIC, 2)
        AS median_monthly_rent,
    ROUND(gross_rental_yield_pct::NUMERIC, 2)
        AS gross_rental_yield_pct,
    ROUND(
        (
            median_resale_price
            / NULLIF(previous_median_resale_price, 0) - 1
        )::NUMERIC * 100,
        2
    ) AS resale_price_growth_pct,
    ROUND(
        (
            median_monthly_rent
            / NULLIF(previous_median_monthly_rent, 0) - 1
        )::NUMERIC * 100,
        2
    ) AS rental_growth_pct,
    ROUND(
        (
            gross_rental_yield_pct
            - previous_gross_rental_yield_pct
        )::NUMERIC,
        2
    ) AS yield_change_points
FROM with_previous_year
ORDER BY
    year,
    town,
    flat_type;