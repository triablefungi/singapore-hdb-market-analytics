# Data Quality Notes

## HDB resale transactions

The resale dataset contains no missing values, invalid transaction months, non-positive resale prices, or non-positive floor areas.

There are 316 additional exact duplicate rows across 315 duplicate groups. These records are retained because the dataset does not provide transaction IDs or unit numbers. Identical rows may therefore represent separate genuine transactions.

The `remaining_lease` field is converted into `remaining_lease_months`, and `storey_range` is separated into lower, upper, and midpoint values.

## HDB rental transactions

The rental dataset contains no missing values, invalid approval months, non-numeric rents, or non-positive monthly rents.

There are 1,516 additional exact duplicate rows across 1,462 duplicate groups. These records are retained because the dataset does not provide rental transaction IDs or unit numbers.

The rental town label `CENTRAL` is standardised to `CENTRAL AREA` to match the resale dataset.

Rental figures are owner-declared and should be treated as indicative.

## MRT station exits

The MRT dataset contains 613 exit records across 190 station names. There are no missing station names, missing exit codes, exact duplicate records, or duplicate coordinates.

Quotation marks embedded in the original GeoJSON property keys are removed during processing. The raw source file remains unchanged.

Each exit is retained as a separate point because proximity to the nearest station entrance is more informative than proximity to a station centroid.

## Duplicate-record policy

Exact duplicates are retained in the cleaned datasets. Without unique transaction or unit identifiers, removing them could incorrectly reduce genuine transaction and rental volumes.

A generated `source_row_id` preserves the position of every record in its respective source file. It is a pipeline identifier and should not be interpreted as an official transaction ID.