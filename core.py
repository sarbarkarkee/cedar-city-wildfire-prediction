"""CS 4150 prototype: real historical labels, chronological evaluation, three agents."""

import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import threading
import time
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import joblib

# Shared settings: folder paths, Cedar City coordinates, distance, and local time.
ROOT = Path(__file__).resolve().parent
CENTER = (37.6837408, -113.095454)
RADIUS = 50
TZ = ZoneInfo("America/Denver")
# Official public data services. No paid AI service is used.
USFS = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_FireOccurrenceCurrentEdition_01/MapServer/0"
NIFC = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Incident_Locations_Current/FeatureServer/0"
POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
FEATURES = [
    "sin_day",
    "cos_day",
    "temperature_max_7d",
    "humidity_7d",
    "wind_7d",
    "rain_7d",
]


def now():
    """Return the current UTC time for saved records."""
    return dt.datetime.now(dt.timezone.utc)


def distance(latitude, longitude):
    """Calculate miles from Cedar City using latitude and longitude."""
    # The haversine formula measures distance along the Earth in miles.
    center_latitude, point_latitude = map(math.radians, [CENTER[0], latitude])
    longitude_change = math.radians(longitude - CENTER[1])
    half_chord = (
        math.sin((point_latitude - center_latitude) / 2) ** 2
        + math.cos(center_latitude)
        * math.cos(point_latitude)
        * math.sin(longitude_change / 2) ** 2
    )
    return 3958.7613 * 2 * math.asin(math.sqrt(min(1, half_chord)))


def fetch(url, parameters=None):
    """Download public JSON data. Report failures instead of inventing data."""
    from urllib.parse import urlencode

    if parameters:
        url += "?" + urlencode(parameters)
    # Use the computer's trusted HTTPS certificates; never disable TLS verification.
    response_text = subprocess.check_output(
        [
            "curl",
            "--fail",
            "-L",
            "--max-time",
            "35",
            "--retry",
            "1",
            "-sS",
            "-H",
            "User-Agent: CedarFire-CS4150/0.1 (local academic prototype)",
            url,
        ],
        stderr=subprocess.PIPE,
        text=True,
        timeout=80,
    )
    response_data = json.loads(response_text)
    if isinstance(response_data, dict) and "error" in response_data:
        raise ValueError(str(response_data["error"])[:200])
    return response_data


def weather_frame(weather_response):
    """Convert NASA readings into a date-sorted table and mark missing values."""
    # NASA uses large negative numbers for missing readings. Convert them to NaN.
    weather_table = pd.DataFrame(weather_response["properties"]["parameter"])
    weather_table.index = pd.to_datetime(weather_table.index, format="%Y%m%d")
    return weather_table.astype(float).mask(lambda values: values <= -900).sort_index()


def features(target_dates, weather_table):
    """Build the six model inputs using only earlier weather and season."""
    # For target day T, use only weather from T-14 through T-8.
    # Requiring all seven days prevents missing readings from silently changing inputs.
    last_date = max(weather_table.index.max(), max(target_dates))
    daily_dates = pd.date_range(weather_table.index.min(), last_date)
    daily_weather_table = weather_table.reindex(daily_dates)
    seven_day_averages = daily_weather_table.rolling(7, min_periods=7).mean()
    past_weather = seven_day_averages.shift(8)
    # Sine/cosine represent the season without a sudden jump at New Year.
    input_rows = []
    for target_date in target_dates:
        day_of_year = target_date.day_of_year
        daily_weather = (
            past_weather.loc[target_date]
            if target_date in past_weather.index
            else pd.Series(dtype=float)
        )
        input_rows.append(
            [
                math.sin(2 * math.pi * day_of_year / 365.25),
                math.cos(2 * math.pi * day_of_year / 365.25),
            ]
            + [
                daily_weather.get(weather_column, np.nan)
                for weather_column in ["T2M_MAX", "RH2M", "WS10M", "PRECTOTCORR"]
            ]
        )
    return np.asarray(input_rows)


def score(model, input_values):
    """Get a model score that can be adjusted into a probability."""
    # SVM/logistic models provide a raw score; MLP provides probabilities.
    # Both paths give one score per row to the probability-adjustment model.
    if hasattr(model, "decision_function"):
        return np.asarray(model.decision_function(input_values)).reshape(-1, 1)
    probabilities = np.clip(model.predict_proba(input_values)[:, 1], 1e-06, 1 - 1e-06)
    return np.log(probabilities / (1 - probabilities)).reshape(-1, 1)


class DataAgent:
    """Agent 1: collect and check official data."""

    name = "01 · Data scout"

    def collect(self, target_date, forecast_days=1):
        """Gather weather inputs, official fire reports, and weather warnings."""
        if forecast_days not in (1, 2, 3):
            raise ValueError("Forecast horizon must be 1, 2 or 3 days")
        result = {
            "agent": self.name,
            "collected_at": now().isoformat(),
            "sources": {},
            "incidents": [],
            "warnings": [],
            "weather": None,
            "forecast": None,
        }

        # One unavailable service should not stop us checking the other services.
        def source(name, get_data):
            """Record whether one source was available; allow other sources to continue."""
            try:
                source_data = get_data()
                result["sources"][name] = {
                    "status": "ok",
                    "retrieved_at": now().isoformat(),
                }
                return source_data
            except Exception as error:
                result["sources"][name] = {
                    "status": "unavailable",
                    "detail": str(error)[:160],
                }
                return None

        # Request enough older weather to build all three daily inputs at once.
        start_date = target_date - dt.timedelta(days=25)
        end_date = (
            target_date + dt.timedelta(days=forecast_days - 1) - dt.timedelta(days=8)
        )
        weather_response = source(
            "NASA POWER",
            lambda: fetch(
                POWER,
                dict(
                    parameters="T2M_MAX,RH2M,WS10M,PRECTOTCORR",
                    community="AG",
                    latitude=CENTER[0],
                    longitude=CENTER[1],
                    start=start_date.strftime("%Y%m%d"),
                    end=end_date.strftime("%Y%m%d"),
                    format="JSON",
                    **{"time-standard": "UTC"},
                ),
            ),
        )
        if weather_response:
            try:
                weather_table = weather_frame(weather_response)
                input_values = features(pd.DatetimeIndex([target_date]), weather_table)
                if not np.isfinite(input_values).all():
                    raise ValueError(
                        "Required lagged weather days are missing; prediction withheld"
                    )
                result["weather"] = {
                    "features": input_values[0].tolist(),
                    "window_start": (target_date - dt.timedelta(days=14)).isoformat(),
                    "window_end": (target_date - dt.timedelta(days=8)).isoformat(),
                    "units": {
                        "temperature": "C",
                        "humidity": "percent",
                        "wind": "m/s",
                        "rain": "mm/day",
                    },
                    "location": list(CENTER),
                }
                result["weather_horizon"] = {}
                # Each prediction day gets its own earlier seven-day weather window.
                for offset in range(forecast_days):
                    prediction_date = target_date + dt.timedelta(days=offset)
                    daily_inputs = features(
                        pd.DatetimeIndex([prediction_date]), weather_table
                    )
                    if np.isfinite(daily_inputs).all():
                        result["weather_horizon"][prediction_date.isoformat()] = {
                            **result["weather"],
                            "features": daily_inputs[0].tolist(),
                            "window_start": (
                                prediction_date - dt.timedelta(days=14)
                            ).isoformat(),
                            "window_end": (
                                prediction_date - dt.timedelta(days=8)
                            ).isoformat(),
                        }
            except Exception as error:
                result["sources"]["NASA POWER"] = {
                    "status": "incomplete",
                    "detail": str(error),
                }

        def incidents():
            """Read all result pages and keep wildfire points inside our radius."""
            local_fires = []
            # The fire service returns results in pages, not necessarily all at once.
            for offset in range(0, 20000, 2000):
                fire_response = fetch(
                    NIFC + "/query",
                    dict(
                        f="json",
                        where="IncidentTypeCategory = 'WF'",
                        geometry=f"{CENTER[1]},{CENTER[0]}",
                        geometryType="esriGeometryPoint",
                        inSR=4326,
                        distance=RADIUS * 1609.344,
                        units="esriSRUnit_Meter",
                        spatialRel="esriSpatialRelIntersects",
                        outFields="*",
                        outSR=4326,
                        returnGeometry="true",
                        resultOffset=offset,
                        resultRecordCount=2000,
                        orderByFields="OBJECTID",
                    ),
                )
                for fire_record in fire_response.get("features", []):
                    fire_info = fire_record["attributes"]
                    fire_location = fire_record.get("geometry") or {}
                    latitude = fire_location.get("y")
                    longitude = fire_location.get("x")
                    # A nearby-state report is not automatically inside our circle.
                    if (
                        latitude is None
                        or longitude is None
                        or distance(latitude, longitude) > RADIUS
                    ):
                        continue
                    local_fires.append(
                        {
                            "id": fire_info.get("UniqueFireIdentifier")
                            or fire_info.get("IrwinID")
                            or str(fire_info.get("OBJECTID")),
                            "name": fire_info.get("IncidentName", "Unnamed incident"),
                            "lat": latitude,
                            "lon": longitude,
                            "distance_miles": round(distance(latitude, longitude), 1),
                            "acres": fire_info.get("DailyAcres")
                            or fire_info.get("IncidentSize"),
                            "contained": fire_info.get("PercentContained"),
                            "out_at": fire_info.get("FireOutDateTime"),
                            "modified": fire_info.get("ModifiedOnDateTime"),
                            "discovered": fire_info.get("FireDiscoveryDateTime"),
                            "source": NIFC,
                        }
                    )
                if not fire_response.get("exceededTransferLimit"):
                    return local_fires
            raise ValueError("Incomplete incident pagination")

        result["incidents"] = source("NIFC WFIGS", incidents) or []
        weather_alerts = source(
            "NWS alerts",
            lambda: fetch(
                "https://api.weather.gov/alerts/active",
                {"area": "UT,NV,AZ", "event": "Red Flag Warning,Fire Weather Watch"},
            ),
        )
        if weather_alerts:
            for alert_record in weather_alerts.get("features", []):
                alert_info = alert_record["properties"]
                geometry = alert_record.get("geometry")
                scope = "state context — exact overlap unverified"
                if geometry:
                    scope = (
                        "within radius"
                        if geometry_intersects(geometry)
                        else "outside radius"
                    )
                # Some warnings name forecast zones instead of providing a shape.
                # Check those zone shapes before treating the warning as local.
                elif alert_info.get("affectedZones"):
                    verified = False
                    for zone in alert_info["affectedZones"]:
                        try:
                            zone_response = fetch(zone)
                            zone_shape = zone_response.get("geometry")
                            if zone_shape and geometry_intersects(zone_shape):
                                scope = "within radius"
                                verified = True
                                break
                            if not zone_shape:
                                raise ValueError("Zone geometry missing")
                        except Exception:
                            break
                    else:
                        verified = True
                        scope = "outside radius"
                if scope == "outside radius":
                    continue
                result["warnings"].append(
                    {
                        "id": alert_record.get("id", alert_info.get("id")),
                        "event": alert_info.get("event"),
                        "headline": alert_info.get("headline"),
                        "description": alert_info.get("description"),
                        "expires": alert_info.get("expires"),
                        "scope": scope,
                        "area": alert_info.get("areaDesc"),
                        "source": alert_info.get("@id") or alert_record.get("id"),
                    }
                )
        location_info = source(
            "NWS forecast",
            lambda: fetch(
                f"https://api.weather.gov/points/{CENTER[0]:.4f},{CENTER[1]:.4f}"
            ),
        )
        if location_info:
            hourly_forecast = source(
                "NWS hourly forecast",
                lambda: fetch(location_info["properties"]["forecastHourly"]),
            )
            if hourly_forecast:
                result["forecast"] = {
                    "updated": hourly_forecast["properties"].get("updateTime"),
                    "periods": hourly_forecast["properties"].get("periods", [])[:24],
                }
        return result


def geometry_intersects(area_shape):
    """Approximate whether a warning area overlaps the circle around Cedar City."""
    # Approximate warning-area overlap on a local map, with a one-mile margin.
    # This is for a prototype, not exact fire-department jurisdiction mapping.
    polygons = (
        [area_shape["coordinates"]]
        if area_shape["type"] == "Polygon"
        else area_shape["coordinates"] if area_shape["type"] == "MultiPolygon" else []
    )
    for polygon in polygons:
        outer_edge = polygon[0]
        map_points = [
            (
                (longitude - CENTER[1]) * 69.172 * math.cos(math.radians(CENTER[0])),
                (latitude - CENTER[0]) * 69.0,
            )
            for longitude, latitude, *_ in outer_edge
        ]
        inside = False
        for (start_x, start_y), (end_x, end_y) in zip(
            map_points, map_points[1:] + map_points[:1]
        ):
            if (start_y > 0) != (end_y > 0) and 0 < (end_x - start_x) * -start_y / (
                end_y - start_y
            ) + start_x:
                inside = not inside
            segment_length_squared = (end_x - start_x) ** 2 + (end_y - start_y) ** 2
            nearest_fraction = (
                max(
                    0,
                    min(
                        1,
                        -(start_x * (end_x - start_x) + start_y * (end_y - start_y))
                        / segment_length_squared,
                    ),
                )
                if segment_length_squared
                else 0
            )
            if (
                math.hypot(
                    start_x + nearest_fraction * (end_x - start_x),
                    start_y + nearest_fraction * (end_y - start_y),
                )
                <= RADIUS + 1
            ):
                return True
        if inside:
            return True
    return False


class PredictionAgent:
    """Agent 2: estimate the chance of a reported wildfire."""

    name = "02 · Risk analyst"

    def __init__(self):
        # Load only our own trained file; joblib files from strangers are unsafe.
        self.bundle = joblib.load(ROOT / "artifacts/model.joblib")

    def predict(self, collected_data, target_date):
        """Use the saved classifier and probability adjustment for one target date."""
        if not collected_data.get("weather"):
            return {
                "agent": self.name,
                "status": "withheld",
                "reason": "Required NASA weather inputs unavailable. No estimate is substituted.",
            }
        # Use the same feature order and saved scaling as during training.
        saved_model = self.bundle
        input_values = np.array([collected_data["weather"]["features"]])
        # Adjust the raw score using the separate probability-calibration years.
        fire_probability = float(
            saved_model["calibrator"].predict_proba(
                score(saved_model["model"], input_values)
            )[0, 1]
        )
        return {
            "agent": self.name,
            "status": "estimated",
            "probability": fire_probability,
            "threshold": 0.5,
            "level": (
                "Elevated" if fire_probability >= 0.5 else "Below prototype threshold"
            ),
            "target_date": target_date.isoformat(),
            "model": saved_model["name"],
            "definition": "At least one recorded wildfire discovery anywhere inside the 50-mile circle on the next America/Denver calendar day. This is a regional historical-risk estimate, not an ignition location or spread forecast.",
            "weather_window": collected_data["weather"],
            "validation": saved_model["report"],
        }


class AlertAgent:
    """Agent 3: save alerts and avoid repeat notifications."""

    name = "03 · Alert coordinator"

    def __init__(self):
        self.path = ROOT / "data/alerts.json"
        self.lock = threading.Lock()
        if not self.path.exists():
            self.path.write_text("[]")

    def history(self):
        """Read previously saved alerts so they can be listed or checked for duplicates."""
        return json.loads(self.path.read_text())

    def emit(self, kind, key, title, body, test=False):
        """Save one new alert unless the same event has already been recorded."""
        # The same event receives the same ID, preventing duplicate notifications.
        alert_id = hashlib.sha256((kind + key).encode()).hexdigest()[:20]
        with self.lock:
            saved_alerts = self.history()
            if any((saved_alert["id"] == alert_id for saved_alert in saved_alerts)):
                return None
            new_alert = {
                "id": alert_id,
                "kind": kind,
                "title": title,
                "body": body,
                "created_at": now().isoformat(),
                "test": test,
                "delivery": "terminal",
                "department_delivery": "disabled",
                "acknowledged": False,
            }
            saved_alerts.insert(0, new_alert)
            self.path.write_text(json.dumps(saved_alerts[:500], indent=2))
            return new_alert

    def evaluate(self, data, prediction):
        """Check model risk, official weather warnings, and recent fire reports."""
        # Model estimates, official warnings, and reported fires are different evidence.
        risk_result = prediction
        if (
            risk_result.get("status") == "estimated"
            and risk_result["probability"] >= risk_result["threshold"]
        ):
            self.emit(
                "model-risk",
                risk_result["target_date"],
                "Prototype regional risk threshold reached",
                f"Model estimate: {risk_result['probability']:.1%} for at least one recorded discovery across the entire region on {risk_result['target_date']}. Verify with official sources. This is not a confirmed fire.",
            )
        for weather_warning in data.get("warnings", []):
            if (
                weather_warning["scope"] == "within radius"
                and weather_warning.get("expires")
                and (
                    dt.datetime.fromisoformat(
                        weather_warning["expires"].replace("Z", "+00:00")
                    )
                    > now()
                )
            ):
                self.emit(
                    "official-weather",
                    weather_warning["id"],
                    weather_warning["event"],
                    f"{weather_warning['headline']}\nExpires: {weather_warning['expires']}\nSource: {weather_warning['source']}\nFire weather warning does not confirm an ignition.",
                )
        # Only recently reported fires that are not out/fully contained trigger alerts.
        for fire in data.get("incidents", []):
            discovery_time = fire.get("discovered")
            is_recent = (
                discovery_time
                and now().timestamp() - discovery_time / 1000 < 48 * 3600
                and (discovery_time / 1000 <= now().timestamp())
            )
            if (
                is_recent
                and (not fire.get("out_at"))
                and ((fire.get("contained") or 0) < 100)
            ):
                self.emit(
                    "reported-incident",
                    fire["id"],
                    "Officially reported wildfire near Cedar City",
                    f"{fire['name']} · {fire['distance_miles']} miles from Cedar City · {fire['lat']}, {fire['lon']}\nReported discovery within 48 hours. Source: {fire['source']}",
                )

    def acknowledge(self, alert_id):
        """Mark a saved alert as read."""
        with self.lock:
            saved_alerts = self.history()
            for saved_alert in saved_alerts:
                if saved_alert["id"] == alert_id:
                    saved_alert["acknowledged"] = True
            self.path.write_text(json.dumps(saved_alerts, indent=2))
