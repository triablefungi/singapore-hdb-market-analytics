/*
Purpose:
Summarise the direction of gross rental-yield changes across HDB
town-flat type combinations from 2024 to 2025.

Method:
1. Calculate median resale prices and monthly rents for 2024 and 2025.
2. Match observations by town, flat type and year.
3. Calculate annual gross rental yields.
4. Compare each combination's 2025 yield with its 2024 yield.
5. Count combinations with declining, unchanged or rising yields.

Gross rental yield:
Median monthly rent x 12 / median resale price x 100

Classification:
Yield changes are rounded to two decimal percentage points before being
classified, matching the precision used in the portfolio analysis.

Eligibility:
Each town-flat type combination must have at least 50 resale records
and 50 rental records in both 2024 and 2025.

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
),

classified_combinations AS (
    SELECT
        *,
        CASE
            WHEN yield_change_points < 0 THEN 'Declining yield'
            WHEN yield_change_points > 0 THEN 'Rising yield'
            ELSE 'Unchanged yield'
        END AS yield_direction
    FROM eligible_combinations
),

direction_summary AS (
    SELECT
        yield_direction,
        COUNT(*) AS town_flat_type_combinations
    FROM classified_combinations
    GROUP BY yield_direction
),

all_directions AS (
    SELECT *
    FROM (
        VALUES
            (1, 'Declining yield'),
            (2, 'Unchanged yield'),
            (3, 'Rising yield')
    ) AS directions(display_order, yield_direction)
)

SELECT
    directions.yield_direction,
    COALESCE(summary.town_flat_type_combinations, 0)
        AS town_flat_type_combinations,
    ROUND(
        COALESCE(summary.town_flat_type_combinations, 0)::NUMERIC
        / NULLIF(
            SUM(
                COALESCE(summary.town_flat_type_combinations, 0)
            ) OVER (),
            0
        ) * 100,
        2
    ) AS share_of_combinations_pct
FROM all_directions AS directions
LEFT JOIN direction_summary AS summary
    ON directions.yield_direction = summary.yield_direction
ORDER BY directions.display_order;