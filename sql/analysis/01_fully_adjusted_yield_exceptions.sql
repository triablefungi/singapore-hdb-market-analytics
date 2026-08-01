/*
Purpose:
Identify the HDB town-flat type combinations that genuinely resisted
rental-yield compression between 2024 and 2025.

Method:
1. Adjust resale prices using fixed 2024 lease-band weights.
2. Adjust monthly rents using fixed 2024 street-level weights.
3. Calculate fully adjusted gross rental yields for 2024 and 2025.

Gross rental yield:
Adjusted monthly rent x 12 / adjusted resale price x 100

Final combinations investigated:
- Geylang - 5 Room
- Bukit Batok - Executive

These were the only apparent yield increases that remained after the
earlier composition checks.
*/

WITH target_combinations AS (
    SELECT *
    FROM (
        VALUES
            ('GEYLANG', '5 ROOM'),
            ('BUKIT BATOK', 'EXECUTIVE')
    ) AS targets(town, flat_type)
),

-- Group resale transactions into lease-commencement bands.
resale_lease_metrics AS (
    SELECT
        resale.town,
        REPLACE(resale.flat_type, '-', ' ') AS flat_type,
        EXTRACT(YEAR FROM resale.transaction_month)::INTEGER AS year,
        CASE
            WHEN resale.lease_commence_date < 1980
                THEN 'Before 1980'
            WHEN resale.lease_commence_date < 1990
                THEN '1980-1989'
            WHEN resale.lease_commence_date < 2000
                THEN '1990-1999'
            ELSE '2000 and later'
        END AS lease_band,
        COUNT(*) AS resale_records,
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY resale.resale_price)
            AS median_resale_price
    FROM hdb_resale AS resale
    INNER JOIN target_combinations AS targets
        ON resale.town = targets.town
        AND REPLACE(resale.flat_type, '-', ' ') =
            targets.flat_type
    WHERE EXTRACT(YEAR FROM resale.transaction_month)
        IN (2024, 2025)
    GROUP BY
        resale.town,
        REPLACE(resale.flat_type, '-', ' '),
        EXTRACT(YEAR FROM resale.transaction_month),
        CASE
            WHEN resale.lease_commence_date < 1980
                THEN 'Before 1980'
            WHEN resale.lease_commence_date < 1990
                THEN '1980-1989'
            WHEN resale.lease_commence_date < 2000
                THEN '1990-1999'
            ELSE '2000 and later'
        END
),

-- Retain lease bands represented in both comparison years.
common_lease_bands AS (
    SELECT
        metrics_2024.town,
        metrics_2024.flat_type,
        metrics_2024.lease_band
    FROM resale_lease_metrics AS metrics_2024
    INNER JOIN resale_lease_metrics AS metrics_2025
        ON metrics_2024.town = metrics_2025.town
        AND metrics_2024.flat_type = metrics_2025.flat_type
        AND metrics_2024.lease_band = metrics_2025.lease_band
    WHERE
        metrics_2024.year = 2024
        AND metrics_2025.year = 2025
),

-- Calculate fixed lease-band weights using the 2024 sales mix.
lease_weights_2024 AS (
    SELECT
        metrics.town,
        metrics.flat_type,
        metrics.lease_band,
        metrics.resale_records::NUMERIC
            / SUM(metrics.resale_records) OVER (
                PARTITION BY metrics.town, metrics.flat_type
            ) AS fixed_weight
    FROM resale_lease_metrics AS metrics
    INNER JOIN common_lease_bands AS common
        ON metrics.town = common.town
        AND metrics.flat_type = common.flat_type
        AND metrics.lease_band = common.lease_band
    WHERE metrics.year = 2024
),

-- Apply the same 2024 lease composition to both years.
adjusted_prices AS (
    SELECT
        metrics.town,
        metrics.flat_type,
        metrics.year,
        SUM(
            metrics.median_resale_price * weights.fixed_weight
        ) AS adjusted_resale_price
    FROM resale_lease_metrics AS metrics
    INNER JOIN lease_weights_2024 AS weights
        ON metrics.town = weights.town
        AND metrics.flat_type = weights.flat_type
        AND metrics.lease_band = weights.lease_band
    GROUP BY
        metrics.town,
        metrics.flat_type,
        metrics.year
),

-- Calculate street-level rental statistics.
rental_street_metrics AS (
    SELECT
        rental.town,
        REPLACE(rental.flat_type, '-', ' ') AS flat_type,
        rental.street_name,
        EXTRACT(YEAR FROM rental.approval_month)::INTEGER AS year,
        COUNT(*) AS rental_records,
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY rental.monthly_rent)
            AS median_monthly_rent
    FROM hdb_rental AS rental
    INNER JOIN target_combinations AS targets
        ON rental.town = targets.town
        AND REPLACE(rental.flat_type, '-', ' ') =
            targets.flat_type
    WHERE EXTRACT(YEAR FROM rental.approval_month)
        IN (2024, 2025)
    GROUP BY
        rental.town,
        REPLACE(rental.flat_type, '-', ' '),
        rental.street_name,
        EXTRACT(YEAR FROM rental.approval_month)
),

-- Retain streets represented in both comparison years.
common_streets AS (
    SELECT
        metrics_2024.town,
        metrics_2024.flat_type,
        metrics_2024.street_name
    FROM rental_street_metrics AS metrics_2024
    INNER JOIN rental_street_metrics AS metrics_2025
        ON metrics_2024.town = metrics_2025.town
        AND metrics_2024.flat_type = metrics_2025.flat_type
        AND metrics_2024.street_name = metrics_2025.street_name
    WHERE
        metrics_2024.year = 2024
        AND metrics_2025.year = 2025
),

-- Calculate fixed street weights using the 2024 rental mix.
street_weights_2024 AS (
    SELECT
        metrics.town,
        metrics.flat_type,
        metrics.street_name,
        metrics.rental_records::NUMERIC
            / SUM(metrics.rental_records) OVER (
                PARTITION BY metrics.town, metrics.flat_type
            ) AS fixed_weight
    FROM rental_street_metrics AS metrics
    INNER JOIN common_streets AS common
        ON metrics.town = common.town
        AND metrics.flat_type = common.flat_type
        AND metrics.street_name = common.street_name
    WHERE metrics.year = 2024
),

-- Apply the same 2024 street composition to both years.
adjusted_rents AS (
    SELECT
        metrics.town,
        metrics.flat_type,
        metrics.year,
        SUM(
            metrics.median_monthly_rent * weights.fixed_weight
        ) AS adjusted_monthly_rent
    FROM rental_street_metrics AS metrics
    INNER JOIN street_weights_2024 AS weights
        ON metrics.town = weights.town
        AND metrics.flat_type = weights.flat_type
        AND metrics.street_name = weights.street_name
    GROUP BY
        metrics.town,
        metrics.flat_type,
        metrics.year
),

-- Combine adjusted prices and rents to calculate gross rental yields.
fully_adjusted_metrics AS (
    SELECT
        prices.town,
        prices.flat_type,
        prices.year,
        prices.adjusted_resale_price,
        rents.adjusted_monthly_rent,
        rents.adjusted_monthly_rent * 12
            / NULLIF(prices.adjusted_resale_price, 0) * 100
            AS fully_adjusted_yield
    FROM adjusted_prices AS prices
    INNER JOIN adjusted_rents AS rents
        ON prices.town = rents.town
        AND prices.flat_type = rents.flat_type
        AND prices.year = rents.year
),

-- Add the preceding year's values for year-over-year comparisons.
with_previous_year AS (
    SELECT
        *,
        LAG(adjusted_resale_price) OVER (
            PARTITION BY town, flat_type
            ORDER BY year
        ) AS previous_adjusted_price,
        LAG(adjusted_monthly_rent) OVER (
            PARTITION BY town, flat_type
            ORDER BY year
        ) AS previous_adjusted_rent,
        LAG(fully_adjusted_yield) OVER (
            PARTITION BY town, flat_type
            ORDER BY year
        ) AS previous_adjusted_yield
    FROM fully_adjusted_metrics
)

SELECT
    town,
    flat_type,
    ROUND(previous_adjusted_price::NUMERIC, 2)
        AS adjusted_price_2024,
    ROUND(adjusted_resale_price::NUMERIC, 2)
        AS adjusted_price_2025,
    ROUND(
        (
            adjusted_resale_price
            / NULLIF(previous_adjusted_price, 0) - 1
        )::NUMERIC * 100,
        2
    ) AS adjusted_price_growth_pct,
    ROUND(previous_adjusted_rent::NUMERIC, 2)
        AS adjusted_rent_2024,
    ROUND(adjusted_monthly_rent::NUMERIC, 2)
        AS adjusted_rent_2025,
    ROUND(
        (
            adjusted_monthly_rent
            / NULLIF(previous_adjusted_rent, 0) - 1
        )::NUMERIC * 100,
        2
    ) AS adjusted_rental_growth_pct,
    ROUND(previous_adjusted_yield::NUMERIC, 2)
        AS fully_adjusted_yield_2024_pct,
    ROUND(fully_adjusted_yield::NUMERIC, 2)
        AS fully_adjusted_yield_2025_pct,
    ROUND(
        (
            fully_adjusted_yield
            - previous_adjusted_yield
        )::NUMERIC,
        2
    ) AS fully_adjusted_yield_change_points
FROM with_previous_year
WHERE year = 2025
ORDER BY
    fully_adjusted_yield_change_points DESC;
