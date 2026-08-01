# Data Sources

This project uses official Singapore Government datasets.

## HDB resale transactions

- Provider: Housing & Development Board
- Source: data.gov.sg
- Dataset ID: `d_8b84c4ee58e3cfc0ece0d773c8ca6abc`
- Coverage: January 2017 onwards
- Format: CSV
- Purpose: Analyse resale prices, transaction volumes, flat characteristics and market trends.

## HDB rental transactions

- Provider: Housing & Development Board
- Source: data.gov.sg
- Dataset ID: `d_c9f57187485a850908655db0e8cfe651`
- Coverage: January 2021 onwards
- Format: CSV
- Purpose: Analyse rental trends and estimate indicative gross rental yields.

Rental figures are owner-declared and should be treated as indicative.

## MRT station exits

- Provider: Land Transport Authority
- Source: data.gov.sg
- Dataset ID: `d_b39d3a0871985372d7e1637193335da5`
- Format: GeoJSON
- Purpose: Measure the proximity of HDB locations to MRT station access points.

## Address geocoding

- Provider: Singapore Land Authority
- Source: OneMap Search API
- Purpose: Convert HDB block and street addresses into geographic coordinates.

OneMap API authentication will be configured separately. Credentials and access tokens must not be committed to Git.