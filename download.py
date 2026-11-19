import json
import math
import time
import urllib.request
import urllib.parse
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
URL = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_FireOccurrenceCurrentEdition_01/MapServer/0/query"
# Ask USFS for reports in a rectangle containing our study area.
query_parameters = {
    "f": "json",
    "where": "fire_year >= 2000",
    "geometry": "-115.0,36.2,-111.1,39.2",
    "geometryType": "esriGeometryEnvelope",
    "inSR": 4326,
    "spatialRel": "esriSpatialRelIntersects",
    "outFields": "fod_id,fire_year,discovery_date,discovery_doy,latitude,longitude,fire_size",
    "returnGeometry": "false",
    "orderByFields": "objectid",
    "resultRecordCount": 2000,
}
fire_records = []
# Download every page before applying the exact radius filter.
for offset in range(0, 100000, 2000):
    query_parameters["resultOffset"] = offset
    for attempt in range(3):
        try:
            response_data = json.loads(
                subprocess.check_output(
                    [
                        "curl",
                        "--fail",
                        "-L",
                        "--max-time",
                        "60",
                        "-sS",
                        URL + "?" + urllib.parse.urlencode(query_parameters),
                    ],
                    text=True,
                )
            )
            if "error" in response_data:
                raise RuntimeError(response_data["error"])
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)
    page_records = [
        fire_record["attributes"] for fire_record in response_data["features"]
    ]
    fire_records += page_records
    print("Downloaded", len(fire_records), flush=True)
    if not response_data.get("exceededTransferLimit"):
        break
else:
    raise RuntimeError("Pagination limit reached")


def distance(latitude, longitude):
    """Calculate miles from Cedar City using latitude and longitude."""
    center_latitude, point_latitude = map(math.radians, [37.6837408, latitude])
    longitude_change = math.radians(longitude + 113.095454)
    return (
        3958.7613
        * 2
        * math.asin(
            math.sqrt(
                math.sin((point_latitude - center_latitude) / 2) ** 2
                + math.cos(center_latitude)
                * math.cos(point_latitude)
                * math.sin(longitude_change / 2) ** 2
            )
        )
    )


# Keep only fire points within 50 miles of Cedar City.
fire_records = [
    fire_record
    for fire_record in fire_records
    if fire_record["latitude"] is not None
    and fire_record["longitude"] is not None
    and (distance(fire_record["latitude"], fire_record["longitude"]) <= 50)
]
(BASE / "data/fires.json").write_text(json.dumps(fire_records))
(BASE / "data/provenance.json").write_text(
    json.dumps(
        {
            "source": URL,
            "edition": "FPA FOD seventh edition, 1992–2024",
            "query": query_parameters,
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "records": len(fire_records),
            "radius_miles": 50,
            "center": [37.6837408, -113.095454],
        },
        indent=2,
    )
)
print("Within radius:", len(fire_records))
