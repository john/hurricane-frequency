#!/usr/bin/env python3
"""hurricane-frequency runner: Poisson frequency model fit to HURDAT2.

Counts historical Atlantic-basin storms whose tracks pass within a given
radius of a target location while at or above a minimum Saffir-Simpson
category, then fits a homogeneous Poisson rate by method of moments:
  lambda = qualifying_event_count / years_observed

Input JSON (positional arg or stdin):
  location.latitude               float
  location.longitude              float
  location.name                   str (passthrough, optional)
  radius_km                       float, default 100
  min_saffir_simpson_category     int 1-5, default 1
  observation_window.start_year   int, default 1900
  observation_window.end_year     int, default latest year in HURDAT2 file

Output JSON (stdout): see README.
"""

import argparse
import json
import math
import os
import sys
from typing import Iterable

EARTH_RADIUS_KM = 6371.0
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATA_SOURCE = "HURDAT2 Atlantic best-track, NOAA NHC"


def find_hurdat2_file() -> str:
    candidates = sorted(
        f for f in os.listdir(DATA_DIR)
        if f.startswith("hurdat2") and f.endswith(".txt")
    )
    if not candidates:
        raise FileNotFoundError(f"No HURDAT2 file found in {DATA_DIR}")
    return os.path.join(DATA_DIR, candidates[-1])


def wind_to_category(wind_kt: float) -> int:
    if wind_kt < 64:
        return 0
    if wind_kt < 83:
        return 1
    if wind_kt < 96:
        return 2
    if wind_kt < 113:
        return 3
    if wind_kt < 137:
        return 4
    return 5


def _parse_lat(token: str) -> float:
    token = token.strip()
    value = float(token[:-1])
    return value if token[-1] == "N" else -value


def _parse_lon(token: str) -> float:
    token = token.strip()
    value = float(token[:-1])
    return value if token[-1] == "E" else -value


def parse_hurdat2(path: str) -> list[dict]:
    storms: list[dict] = []
    with open(path, "r") as fh:
        lines = [line.strip() for line in fh if line.strip()]
    i = 0
    while i < len(lines):
        header_parts = [p.strip() for p in lines[i].split(",")]
        storm_id, name, n_records = header_parts[0], header_parts[1], int(header_parts[2])
        i += 1
        points = []
        for _ in range(n_records):
            row = [p.strip() for p in lines[i].split(",")]
            i += 1
            year = int(row[0][:4])
            lat = _parse_lat(row[4])
            lon = _parse_lon(row[5])
            wind = float(row[6])
            points.append({"year": year, "lat": lat, "lon": lon, "wind_kt": wind})
        if points:
            storms.append({
                "id": storm_id,
                "name": name,
                "year": points[0]["year"],
                "points": points,
            })
    return storms


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def count_qualifying_events(
    storms: Iterable[dict],
    target_lat: float,
    target_lon: float,
    radius_km: float,
    min_category: int,
    start_year: int,
    end_year: int,
) -> int:
    count = 0
    for storm in storms:
        if storm["year"] < start_year or storm["year"] > end_year:
            continue
        for pt in storm["points"]:
            if wind_to_category(pt["wind_kt"]) < min_category:
                continue
            if haversine_km(target_lat, target_lon, pt["lat"], pt["lon"]) <= radius_km:
                count += 1
                break
    return count


def _validate(input_data: dict) -> None:
    loc = input_data.get("location")
    if not isinstance(loc, dict):
        raise ValueError("'location' object is required.")
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    if not isinstance(lat, (int, float)) or not -90 <= lat <= 90:
        raise ValueError("'location.latitude' must be a number in [-90, 90].")
    if not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
        raise ValueError("'location.longitude' must be a number in [-180, 180].")

    cat = input_data.get("min_saffir_simpson_category", 1)
    if not isinstance(cat, int) or isinstance(cat, bool) or not 1 <= cat <= 5:
        raise ValueError("'min_saffir_simpson_category' must be an integer in [1, 5].")

    radius = input_data.get("radius_km", 100)
    if not isinstance(radius, (int, float)) or radius <= 0:
        raise ValueError("'radius_km' must be a positive number.")


def run(input_data: dict) -> dict:
    _validate(input_data)

    loc = input_data["location"]
    target_lat = float(loc["latitude"])
    target_lon = float(loc["longitude"])
    location_name = loc.get("name")

    radius_km = float(input_data.get("radius_km", 100))
    min_category = int(input_data.get("min_saffir_simpson_category", 1))

    hurdat2_path = find_hurdat2_file()
    storms = parse_hurdat2(hurdat2_path)
    latest_year = max(s["year"] for s in storms)

    window = input_data.get("observation_window", {}) or {}
    start_year = int(window.get("start_year", 1900))
    end_year = int(window.get("end_year", latest_year))
    if start_year > end_year:
        raise ValueError("observation_window.start_year must be <= end_year.")

    count = count_qualifying_events(
        storms, target_lat, target_lon, radius_km, min_category, start_year, end_year
    )
    years = end_year - start_year + 1
    lambda_annual = count / years if years > 0 else 0.0
    p_at_least_one = 1.0 - math.exp(-lambda_annual)

    metadata_location = {"latitude": target_lat, "longitude": target_lon}
    if location_name is not None:
        metadata_location["name"] = location_name

    return {
        "lambda_annual": lambda_annual,
        "probability_at_least_one_per_year": p_at_least_one,
        "historical_event_count": count,
        "observation_years": years,
        "expected_events_in_3yr_term": 3 * lambda_annual,
        "metadata": {
            "location": metadata_location,
            "radius_km": radius_km,
            "min_saffir_simpson_category": min_category,
            "observation_window": {"start_year": start_year, "end_year": end_year},
            "data_source": DATA_SOURCE,
            "data_version": os.path.basename(hurdat2_path),
        },
    }


def _load_input_json() -> dict:
    parser = argparse.ArgumentParser(
        description="hurricane-frequency runner: Poisson rate from HURDAT2."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Path to input JSON file, or '-' to read from stdin (default).",
    )
    args = parser.parse_args()
    if args.input == "-":
        return json.load(sys.stdin)
    with open(args.input, "r", encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    output = run(_load_input_json())
    json.dump(output, sys.stdout, indent=2)
    print()
