/*
Purpose:
Provide the detailed evidence behind the 2025 HDB rental-yield
compression summary.

Method:
1. Calculate median resale prices and monthly rents for 2024 and 2025.
2. Match observations by town, flat type and year.
3. Retain combinations meeting the minimum sample-size requirement.
4. Compare resale prices, rents and gross rental yields across both years.
5. Classify each combination by its rounded yield change.

Gross rental yield:
Median monthly rent x 12 / median resale price x 100

Eligibility:
Each town-flat type combination must have at least 50 resale records
and 50 rental records in both 2024 and 2025.

Classification:
Yield changes are rounded to two decimal percentage points before being
classified, matching the precision used in the portfolio analysis.

Note:
These are unadjusted market-level estimates. Changes in lease age,
street composition and transaction mix may affect individual results.
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
    WHERE EXTRACT(YEAR FROM transaction_month) IN (2024, 2025)
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
    WHERE EXTRACT(YEAR FROM approval_month) IN (2024, 2025)
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

year_comparison AS (
    SELECT
        yields_2025.town,
        yields_2025.flat_type,
        yields_2024.resale_records AS resale_records_2024,
        yields_2025.resale_records AS resale_records_2025,
        yields_2024.rental_records AS rental_records_2024,
        yields_2025.rental_records AS rental_records_2025,
        yields_2024.median_resale_price
            AS median_resale_price_2024,
        yields_2025.median_resale_price
            AS median_resale_price_2025,
        yields_2024.median_monthly_rent
            AS median_monthly_rent_2024,
        yields_2025.median_monthly_rent
            AS median_monthly_rent_2025,
        yields_2024.gross_rental_yield_pct
            AS gross_rental_yield_2024_pct,
        yields_2025.gross_rental_yield_pct
            AS gross_rental_yield_2025_pct,
        ROUND(
            (
                yields_2025.gross_rental_yield_pct
                - yields_2024.gross_rental_yield_pct
            )::NUMERIC,
            2
        ) AS yield_change_points
    FROM annual_yields AS yields_2024
    INNER JOIN annual_yields AS yields_2025
        ON yields_2024.town = yields_2025.town
        AND yields_2024.flat_type = yields_2025.flat_type
    WHERE
        yields_2024.year = 2024
        AND yields_2025.year = 2025
),

eligible_combinations AS (
    SELECT *
    FROM year_comparison
    WHERE
        resale_records_2024 >= 50
        AND resale_records_2025 >= 50
        AND rental_records_2024 >= 50
        AND rental_records_2025 >= 50
)

SELECT
    town,
    flat_type,
    resale_records_2024,
    resale_records_2025,
    rental_records_2024,
    rental_records_2025,
    ROUND(median_resale_price_2024::NUMERIC, 2)
        AS median_resale_price_2024,
    ROUND(median_resale_price_2025::NUMERIC, 2)
        AS median_resale_price_2025,
    ROUND(
        (
            median_resale_price_2025
            / NULLIF(median_resale_price_2024, 0) - 1
        )::NUMERIC * 100,
        2
    ) AS resale_price_growth_pct,
    ROUND(median_monthly_rent_2024::NUMERIC, 2)
        AS median_monthly_rent_2024,
    ROUND(median_monthly_rent_2025::NUMERIC, 2)
        AS median_monthly_rent_2025,
    ROUND(
        (
            median_monthly_rent_2025
            / NULLIF(median_monthly_rent_2024, 0) - 1
        )::NUMERIC * 100,
        2
    ) AS rental_growth_pct,
    ROUND(gross_rental_yield_2024_pct::NUMERIC, 2)
        AS gross_rental_yield_2024_pct,
    ROUND(gross_rental_yield_2025_pct::NUMERIC, 2)
        AS gross_rental_yield_2025_pct,
    yield_change_points,
    CASE
        WHEN yield_change_points < 0 THEN 'Declining yield'
        WHEN yield_change_points > 0 THEN 'Rising yield'
        ELSE 'Unchanged yield'
    END AS yield_direction
FROM eligible_combinations
ORDER BY
    yield_change_points DESC,
    town,
    flat_type;