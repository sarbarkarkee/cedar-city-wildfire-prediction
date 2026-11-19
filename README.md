# Cedar City Wildfire Prediction — Team Code Guide

This guide explains what each Python file does and what the main code inside it means. Our CS 4150 prototype estimates the chance of a wildfire report within 50 miles of Cedar City, Utah.

## How the files work together

For training: `train.py` reads the saved data, uses calculations from `core.py`, and saves the trained model.

For predictions: `main.py` → `demo.py` → `forecast.py` → the three agents in `core.py`. The results appear in the terminal. If email is enabled, `email_alerts.py` handles sending.

## main.py — starts the program

- `main()` reads the options typed in the terminal.
- `--alerts` reads and prints alerts that were saved before.
- `--watch` with `--live` repeats the check. `--interval` sets the time between checks in seconds.
- `run_demo()` calls the main function from `demo.py` to run the chosen example or prediction.
- The loop keeps monitoring until we stop it with Ctrl+C. Errors are shown so a failed update is not treated as a safe result.
- `if __name__ == "__main__"` starts the program when we run this file directly.

## core.py — the three agents and shared calculations

This is the main logic used by the other files. The agents are Python classes, with each class doing one job.

### Shared settings and functions

- `ROOT` is the project folder. `CENTER` is Cedar City’s latitude and longitude. `RADIUS` is 50 miles. `TZ` is the local time zone.
- `FEATURES` lists the six numbers given to the model, in the correct order.
- `now()` gives the current time for saved records.
- `distance()` calculates how far a fire report is from Cedar City.
- `fetch()` requests data from a public service and reports download errors.
- `weather_frame()` turns NASA weather data into a table ordered by date. Missing readings stay missing.
- `features()` builds the model inputs: season, temperature, humidity, wind, and rain. Season uses two numbers, making six inputs in total. For target day T, it averages weather from T−14 through T−8. It does not use weather from the day being predicted.
- `score()` gets a model score in a form that can be adjusted into a probability.
- `geometry_intersects()` helps check whether a weather-warning area overlaps our study area.

### DataAgent — gets information

`collect()` gets earlier weather from NASA Prediction Of Worldwide Energy Resources (POWER), weather forecasts and warnings from the National Weather Service (NWS), and fire reports from the National Interagency Fire Center (NIFC). It prepares the model inputs and records which sources worked. If one source fails, it still tries the others.

### PredictionAgent — estimates risk

- `__init__()` loads our saved model from `artifacts/model.joblib`.
- `predict()` passes the prepared weather inputs through the saved model and probability adjustment.
- It returns the date, estimated chance, model name, and alert threshold. The chosen prototype threshold is 50%.
- If required weather is missing, it returns “withheld” instead of making up a prediction.

### AlertAgent — checks and saves alerts

- `history()` reads saved alerts from `data/alerts.json`.
- `emit()` gives an event a consistent ID and saves it only if that event has not already been recorded.
- `evaluate()` checks three separate things: model risk at or above 50%, active weather warnings in the area, and recent official fire reports. A model risk alert does not mean a fire is confirmed.
- `acknowledge()` marks a saved alert as read.

## forecast.py — shows the next three days

`show_next_three_days()` starts with tomorrow in Cedar City’s local time. It collects data once, then loops over three dates. Each date gets its own inputs and risk estimate.

It prints the date, chance of a fire report, and whether the risk reaches 50%. It asks the Alert Agent to check alerts, saves results in `data/three_day_results.json`, and can pass new alerts to the email file when sending is enabled. Missing inputs show as unavailable.

## train.py — trains and compares the models

`train_models()` performs these steps:

1. Reads past fire reports and weather data.
2. Uses `features()` to prepare the six input numbers for each day.
3. Creates a label: 1 means at least one fire was recorded that day; 0 means no fire was recorded.
4. Splits dates into training (2000–2017), model selection (2018–2019), probability adjustment (2020–2021), and final testing (2022–2024).
5. Uses `StandardScaler` to put inputs on comparable scales. The scaling is learned from training data only.
6. Trains Logistic Regression, a Multi-Layer Perceptron (MLP) neural network, and a Support Vector Machine (SVM) with a Radial Basis Function (RBF) kernel.
7. Chooses the model with the lowest Brier score on the selection years. Lower means smaller probability errors.
8. Adjusts its probabilities using the separate adjustment years, then evaluates it on the final test years.
9. Saves the model in `artifacts/model.joblib`, results in `artifacts/metrics.json`, and test predictions in `data/Model Data/test_predictions.csv`.

The final test data is kept separate from learning and model selection. Precision measures how often alerts match recorded fire days. Recall measures how many recorded fire days were caught.

## demo.py — runs examples and controls the displayed results

- `run_details()` runs a historical or live example. A historical example uses the included data and compares the prediction with what was actually recorded.
- `main()` chooses the mode. A normal run calls the three-day forecast. A date or test-alert option runs the corresponding example.
- `main()` also keeps the usual terminal output short. `--details` shows the longer explanation.
- `heading()` prints headings for the detailed mode.
- `email_result()` changes the email sending status into a readable message.
- Test alerts are marked as tests. Past predictions are not sent as current fire warnings.

## download.py — downloads fire history

The main code runs when this script is started. It requests United States Forest Service (USFS) fire records in batches because the service limits how many records it returns at once. It retries failed requests.

`distance()` calculates each report’s distance from Cedar City. The code keeps only reports within 50 miles, then saves `data/fires.json`. It also saves the source and download details in `data/provenance.json`. The ZIP already includes the downloaded data, so this script is optional for the class demo.

## export_data.py — creates readable data files

`export()` reads the downloaded data and writes comma-separated values (CSV) files:

- `data/US Forest Service/` contains fire history, readable dates, and distances.
- `data/NASA/` contains daily weather history.
- `data/Model Data/` contains the model inputs, fire labels, and date groups used for training and testing.

It calls the same `features()` function used during training so the input calculations stay consistent.

## email_alerts.py — sends email when configured

- The first code section reads local settings from `.env`, if that file exists. Passwords should stay out of GitHub.
- `email_status()` checks whether a sender is configured and whether email is enabled.
- `mail()` builds the subject and message, then sends it using Simple Mail Transfer Protocol (SMTP) over an encrypted connection.
- It records whether the email provider accepted the message or sending failed. Provider acceptance does not prove inbox delivery.
- Email is disabled by default. Fire departments are not contacted.

## tests/test_core.py — project checks (inside the ZIP)

This file checks important calculations and agent behavior. Run the checks from the extracted project folder with:

```bash
python -m unittest discover -s tests -v
```

## Useful variable names

| Name | Meaning |
| --- | --- |
| `target_date` | The day we want to predict. |
| `weather_table` | Weather readings arranged by date. |
| `input_values` | The numbers passed to the model. |
| `fire_labels` | The recorded answer for each day: 1 or 0. |
| `fire_probability` | The model’s estimated chance of a fire report. |
| `collected_data` | Information gathered by the Data Agent. |
| `saved_alerts` | Alerts already stored by the program. |

`np` means NumPy, `pd` means pandas, and `dt` means Python’s datetime module. A `def` block defines a function. A `class` groups related data and functions. `self` refers to the current object.

## Run the project

Download and extract **CedarFire_Complete_Project.zip**, then open **CedarFire-CS4150** in Visual Studio Code (VS Code). Run these commands in that folder:

```bash
python -m pip install -r requirements.txt
python train.py
python main.py
```

The last command gets current data and shows the next three days. For a repeatable historical example, use `python main.py --date 2024-07-01`. Some computers use `python3` instead of `python`. The presentation is a separate `.pptx` download.

The estimates concern a fire report somewhere in the whole area. They do not locate an exact ignition. Three-day estimates reuse the daily model and still need further testing. This is a student prototype, not an official warning system.
