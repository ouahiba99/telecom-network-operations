import json
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from shapely.geometry import Point, shape

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

BOUNDARIES_PATH = (
    BASE_DIR
    / "data"
    / "geography"
    / "wilaya-boundaries.geojson"
)

WILAYAS_PATH = (
    BASE_DIR
    / "data"
    / "geography"
    / "wilayas.json"
)

GEO_SOURCE = "geoalgeria_69_wilaya_boundaries"


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB", "telecom_network"),
        user=os.getenv("POSTGRES_USER", "telecom"),
        password=os.getenv("POSTGRES_PASSWORD", "telecom"),
    )


def load_wilaya_metadata():
    with open(WILAYAS_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        int(item["code"]): item
        for item in data["wilayas"]
    }


def load_boundaries():
    with open(BOUNDARIES_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    boundaries = []

    for feature in data["features"]:
        code = int(feature["properties"]["code"])
        geometry = shape(feature["geometry"])

        boundaries.append(
            {
                "code": code,
                "geometry": geometry,
            }
        )

    return boundaries


def find_wilaya(longitude, latitude, boundaries):
    point = Point(longitude, latitude)

    for boundary in boundaries:
        if boundary["geometry"].covers(point):
            return boundary["code"]

    return None


def main():
    print("=== Geographic Cell Enrichment ===")
    print()

    if not BOUNDARIES_PATH.exists():
        raise FileNotFoundError(
            f"Missing boundary file: {BOUNDARIES_PATH}"
        )

    if not WILAYAS_PATH.exists():
        raise FileNotFoundError(
            f"Missing Wilaya metadata file: {WILAYAS_PATH}"
        )

    print(f"Boundary source: {BOUNDARIES_PATH}")
    print(f"Metadata source: {WILAYAS_PATH}")
    print()

    metadata = load_wilaya_metadata()
    boundaries = load_boundaries()

    print(f"Wilaya metadata loaded: {len(metadata)}")
    print(f"Boundary geometries loaded: {len(boundaries)}")
    print()

    conn = get_connection()

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

            cells = cursor.fetchall()

            print(f"Cells to process: {len(cells):,}")
            print()

            matched = 0
            boundary_review = 0

            for cell_id, latitude, longitude in cells:
                wilaya_code = find_wilaya(
                    longitude,
                    latitude,
                    boundaries,
                )

                if wilaya_code is not None:
                    wilaya = metadata.get(wilaya_code)

                    if wilaya is None:
                        wilaya_name = None
                        wilaya_name_fr = None
                        status = "BOUNDARY_REVIEW"
                        boundary_review += 1
                    else:
                        wilaya_name = wilaya.get("name_en")
                        wilaya_name_fr = wilaya.get("name_fr")
                        status = "MATCHED"
                        matched += 1

                    cursor.execute(
                        """
                        UPDATE cells
                        SET
                            wilaya_code = %s,
                            wilaya_name = %s,
                            wilaya_name_fr = %s,
                            geo_match_status = %s,
                            geo_source = %s
                        WHERE id = %s;
                        """,
                        (
                            wilaya_code,
                            wilaya_name,
                            wilaya_name_fr,
                            status,
                            GEO_SOURCE,
                            cell_id,
                        ),
                    )

                else:
                    cursor.execute(
                        """
                        UPDATE cells
                        SET
                            wilaya_code = NULL,
                            wilaya_name = NULL,
                            wilaya_name_fr = NULL,
                            geo_match_status = 'BOUNDARY_REVIEW',
                            geo_source = %s
                        WHERE id = %s;
                        """,
                        (
                            GEO_SOURCE,
                            cell_id,
                        ),
                    )

                    boundary_review += 1

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    print("=== Enrichment Complete ===")
    print(f"Matched:          {matched:,}")
    print(f"Boundary review:  {boundary_review:,}")
    print(f"Total processed:  {matched + boundary_review:,}")


if __name__ == "__main__":
    main()
