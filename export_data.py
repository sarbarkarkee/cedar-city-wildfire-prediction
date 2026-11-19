"""Export downloaded official data and model-ready examples as readable CSV files."""

import csv
import json
import numpy as np
import pandas as pd
from core import ROOT, FEATURES, distance, features, weather_frame


def export():
    """Create readable CSV copies of the real downloaded data."""
    for folder in ["US Forest Service", "NASA", "Model Data"]:
        (ROOT / "data" / folder).mkdir(parents=True, exist_ok=True)
    # Preserve original agency data and add readable date/distance columns.
    fire_records = json.loads((ROOT / "data/fires.json").read_text())
    fire_table = pd.DataFrame(fire_records)
    fire_table["discovery_day"] = pd.to_datetime(
        fire_table["discovery_date"], unit="ms"
    ).dt.strftime("%Y-%m-%d")
    fire_table["distance_miles"] = fire_table.apply(
        lambda fire_row: round(distance(fire_row.latitude, fire_row.longitude), 4),
        axis=1,
    )
    fire_table.to_csv(
        ROOT / "data/US Forest Service/fire_history_50_miles.csv", index=False
    )
    weather_table = weather_frame(
        json.loads((ROOT / "data/weather_history.json").read_text())
    )
    weather_table.rename_axis("date_utc").to_csv(
        ROOT / "data/NASA/weather_history.csv", date_format="%Y-%m-%d"
    )
    target_dates = pd.date_range("2000-01-15", "2024-12-31")
    input_values = features(target_dates, weather_table)
    reported_fire_dates = set(
        pd.to_datetime(fire_table["discovery_date"], unit="ms").dt.normalize()
    )
    # One row = one target day. The label says whether a fire was reported.
    training_table = pd.DataFrame(input_values, columns=FEATURES)
    training_table.insert(0, "target_date", target_dates.strftime("%Y-%m-%d"))
    training_table["fire_reported"] = np.array(
        [int(target_date in reported_fire_dates) for target_date in target_dates]
    )
    training_table["split"] = np.select(
        [
            target_dates.year <= 2017,
            target_dates.year <= 2019,
            target_dates.year <= 2021,
        ],
        ["train", "selection", "calibration"],
        default="test",
    )
    training_table = training_table.loc[np.isfinite(input_values).all(axis=1)]
    training_table.to_csv(ROOT / "data/Model Data/training_data.csv", index=False)
    print(
        f"Exported {len(fire_table):,} historical fire records, {len(weather_table):,} weather days, and {len(training_table):,} training examples."
    )
    print(
        "All CSVs are in data/. These are conversions of the downloaded official data, not synthetic data."
    )


if __name__ == "__main__":
    export()
