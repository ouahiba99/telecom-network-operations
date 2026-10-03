import json
import os

import psycopg2
from shapely.geometry import Point, shape


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GEOJSON_PATH = os.path.join(
    BASE_DIR,
    "data",
    "geography",
    "wilaya-boundaries.geojson",
)

WILAYAS_PATH = os.path.join(
    BASE_DIR,
    "data",
    "geography",
    "wilayas.json",
)


def load_boundaries():
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        geojson = json.load(f)

    with open(WILAYAS_PATH, encoding="utf-8") as f:
        metadata = json.load(f)

    metadata_by_code = {
        item["code"]: item
        for item in metadata["wilayas"]
    }

    boundaries = []

    for feature in geojson["features"]:
        code = feature["properties"]["code"]

        boundaries.append(
            {
                "code": code,
                "name_en": metadata_by_code[code]["name_en"],
                "name_fr": metadata_by_code[code]["name_fr"],
                "geometry": shape(feature["geometry"]),
            }
        )

    return boundaries


def get_cells():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB", "telecom_network"),
        user=os.getenv("POSTGRES_USER", "telecom"),
        password=os.getenv("POSTGRES_PASSWORD", "telecom"),
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    latitude,
                    longitude
                FROM cells
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                ORDER BY id;
                """
            )

            return cursor.fetchall()
    finally:
        conn.close()


def find_wilaya(latitude, longitude, boundaries):
    point = Point(longitude, latitude)

    for boundary in boundaries:
        if boundary["geometry"].covers(point):
            return boundary

    return None


def main():
    print("Loading Wilaya boundaries...")
    boundaries = load_boundaries()

    print(f"Loaded boundaries: {len(boundaries)}")

    print("Loading cells from PostgreSQL...")
    cells = get_cells()

    print(f"Loaded cells: {len(cells):,}")
    print()

    matched = 0
    unmatched = 0

    matches = {}

    unmatched_samples = []

    for cell_id, latitude, longitude in cells:
        wilaya = find_wilaya(
            latitude,
            longitude,
            boundaries,
        )

        if wilaya:
            matched += 1

            code = wilaya["code"]

            if code not in matches:
                matches[code] = {
                    "name_en": wilaya["name_en"],
                    "name_fr": wilaya["name_fr"],
                    "cells": 0,
                }

            matches[code]["cells"] += 1

        else:
            unmatched += 1

            if len(unmatched_samples) < 20:
                unmatched_samples.append(
                    {
                        "cell_id": cell_id,
                        "latitude": latitude,
                        "longitude": longitude,
                    }
                )

    print("=== ENRICHMENT VALIDATION ===")
    print(f"Total cells:     {len(cells):,}")
    print(f"Matched:         {matched:,}")
    print(f"Unmatched:       {unmatched:,}")

    if cells:
        coverage = matched * 100 / len(cells)
        print(f"Coverage:        {coverage:.2f}%")

    print()
    print("=== CELLS BY WILAYA ===")

    for code, data in sorted(
        matches.items(),
        key=lambda item: item[1]["cells"],
        reverse=True,
    ):
        print(
            f"{code:02d} | "
            f"{data['name_en']:<20} | "
            f"{data['cells']:>6,}"
        )

    print()

    if unmatched_samples:
        print("=== UNMATCHED SAMPLE ===")

        for item in unmatched_samples:
            print(
                f"cell={item['cell_id']} "
                f"lat={item['latitude']} "
                f"lon={item['longitude']}"
            )
    else:
        print("No unmatched cells.")


if __name__ == "__main__":
    main()
