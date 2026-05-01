# hurricane-frequency

A simple Poisson frequency model fit to HURDAT2 historical Atlantic best-track
data. Given a target location, search radius, minimum Saffir-Simpson category,
and observation window, it returns the annual rate λ at which qualifying
storms have historically passed within range of the target.

It is the first step in a cat-bond demo pipeline:

```
hurricane-frequency  →  CLIMADA  →  OasisLMF  →  FinancePy
```

## Usage

```bash
# from the repo root
python runner.py data/input_data.json

# or via stdin
python runner.py < data/input_data.json
```

### Docker

```bash
docker build -t model-home/hurricane_frequency:latest .
docker run --rm model-home/hurricane_frequency:latest                  # uses bundled example
docker run --rm -v "$PWD/run:/run" model-home/hurricane_frequency:latest /run/query.json
```

## Example I/O

Input (`data/input_data.json`):

```json
{
  "location": { "latitude": 25.7617, "longitude": -80.1918, "name": "Miami, FL" },
  "radius_km": 100,
  "min_saffir_simpson_category": 4,
  "observation_window": { "start_year": 1900, "end_year": 2024 }
}
```

Output:

```json
{
  "lambda_annual": 0.056,
  "probability_at_least_one_per_year": 0.0545,
  "historical_event_count": 7,
  "observation_years": 125,
  "expected_events_in_3yr_term": 0.168,
  "metadata": {
    "location": { "latitude": 25.7617, "longitude": -80.1918, "name": "Miami, FL" },
    "radius_km": 100,
    "min_saffir_simpson_category": 4,
    "observation_window": { "start_year": 1900, "end_year": 2024 },
    "data_source": "HURDAT2 Atlantic best-track, NOAA NHC",
    "data_version": "hurdat2-1851-2024-040425.txt"
  }
}
```

## Method

1. Parse HURDAT2 into storms (header line + N six-hour track records).
2. Map max sustained wind in knots to Saffir-Simpson category (≥64 → 1, ≥83 → 2,
   ≥96 → 3, ≥113 → 4, ≥137 → 5).
3. For each storm whose year falls in `[start_year, end_year]`, count it as one
   event if any single track point is within `radius_km` of the target *and* at
   or above `min_saffir_simpson_category`. Each storm counts at most once.
4. Fit by method of moments: `λ = count / (end_year - start_year + 1)`.

## Simplifications / known limitations

This is a demo model. Deliberately not implemented:

- **Method of moments only.** No Bayesian fit, no negative-binomial, no
  uncertainty interval. If `count == 0` the estimate is `λ = 0`, even though
  zero observed events does not mean zero true rate.
- **Point-in-radius proxy for landfall.** No coastline polyline crossing —
  any track point within `radius_km` of the target counts.
- **No climate conditioning** (Knutson scaling, RCP scenarios, decadal
  oscillations). The full window is treated as stationary.
- **No track interpolation.** HURDAT2 6-hourly records are used as-is, so a
  fast-moving storm could in principle skip across the radius between samples.
- **No decay model, no asymmetric wind field, no physics.**

## Tests

```bash
python -m pytest tests/
```
