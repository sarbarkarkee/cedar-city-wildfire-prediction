"""Plain-language terminal presentation of the three-agent wildfire project."""

import argparse
import datetime as dt
import json
import secrets
import pandas as pd
from core import (
    ROOT,
    RADIUS,
    TZ,
    DataAgent,
    PredictionAgent,
    AlertAgent,
    features,
    weather_frame,
)


def heading(title):
    """Print a heading only when the detailed explanation is requested."""
    print("\n" + title)
    print("-" * len(title))


def email_result(result):
    """Describe email success or failure without exposing login details."""
    status = result["status"]
    if status == "accepted_by_smtp":
        print(
            "  The email provider accepted the message. Check your inbox and spam folder."
        )
    elif status == "not_sent":
        print(
            "  Email was not sent. Connect a sending account with setup_email.py first."
        )
    else:
        print("  Email could not be sent. Please check the sending account settings.")


def run_details(argv=None):
    """Run an optional detailed historical or live demonstration."""
    argument_parser = argparse.ArgumentParser(
        description="Explain and run the Cedar City wildfire model in the terminal."
    )
    argument_parser.add_argument(
        "--live",
        action="store_true",
        help="Get current official data and estimate tomorrow’s risk.",
    )
    argument_parser.add_argument(
        "--date",
        default="2024-07-01",
        help="Historical test date, YYYY-MM-DD, in 2022–2024.",
    )
    argument_parser.add_argument(
        "--test-alert",
        action="store_true",
        help="Save a local demonstration alert. No email is sent.",
    )
    argument_parser.add_argument(
        "--send-test-email",
        action="store_true",
        help="Send a TEST email using your local sender setup.",
    )
    argument_parser.add_argument(
        "--send-email",
        action="store_true",
        help="Email new live alerts. Requires --live.",
    )
    argument_parser.add_argument(
        "--details", action="store_true", help="Show the longer project explanation."
    )
    options = argument_parser.parse_args(argv)
    if options.send_email and (not options.live):
        argument_parser.error(
            "--send-email requires --live. Past predictions are never emailed as current warnings."
        )
    prediction_agent = PredictionAgent()
    alert_agent = AlertAgent()
    report = prediction_agent.bundle["report"]
    fire_records = json.loads((ROOT / "data/fires.json").read_text())
    print("=" * 68)
    print("CEDAR CITY WILDFIRE PREDICTION | CS 4150 CLASS PROJECT")
    print("=" * 68)
    print(f"Place: Cedar City, Utah, and places within {RADIUS} miles.")
    print("Goal: estimate whether one or more wildfires will be reported")
    print("somewhere in this area on the next local calendar day.")
    print("The program uses three helpers, called agents.")
    print("This is a student prototype, not an official emergency warning.")
    if options.live:
        target_date = dt.datetime.now(TZ).date() + dt.timedelta(days=1)
        print("Mode: LIVE DATA. The date below is tomorrow in Cedar City.")
    else:
        try:
            target_date = dt.date.fromisoformat(options.date)
        except ValueError:
            argument_parser.error("Enter a date as YYYY-MM-DD.")
        if not dt.date(2022, 1, 1) <= target_date <= dt.date(2024, 12, 31):
            argument_parser.error(
                "Choose a historical test date from 2022 through 2024."
            )
        print("Mode: HISTORICAL CLASSROOM DEMO. This is NOT today’s forecast.")
        print("We make a prediction for a past test date, then check what happened.")
    heading("1. DATA AGENT — gets the information")
    print(
        f"  Past fire reports: {len(fire_records):,}, from 2000–2024, inside {RADIUS} miles."
    )
    print("  Fire source: US Forest Service (official reported fire history).")
    print("  Weather source: NASA POWER (temperature, air moisture, wind, rain).")
    print("  Live-only sources: National Weather Service warnings and forecasts;")
    print("                     National Interagency Fire Center fire reports.")
    if options.live:
        print(
            "  Getting current official information. This can take a little time...",
            flush=True,
        )
        collected_data = DataAgent().collect(target_date)
        for name, status in collected_data["sources"].items():
            text = "received" if status["status"] == "ok" else "missing or incomplete"
            print(f"  {name}: {text}.")
    else:
        weather_table = weather_frame(
            json.loads((ROOT / "data/weather_history.json").read_text())
        )
        input_values = features(pd.DatetimeIndex([target_date]), weather_table)
        collected_data = {
            "weather": {
                "features": input_values[0].tolist(),
                "window_start": (target_date - dt.timedelta(days=14)).isoformat(),
                "window_end": (target_date - dt.timedelta(days=8)).isoformat(),
            },
            "incidents": [],
            "warnings": [],
        }
        print(
            "  Reading the real downloaded files. No internet is needed for this demo."
        )
    if collected_data.get("weather"):
        weather_details = collected_data["weather"]
        weather_inputs = weather_details["features"]
        print(
            f"  Earlier weather used: {weather_details['window_start']} through {weather_details['window_end']} (UTC dates)."
        )
        print("  These are averages over seven days, measured near Cedar City:")
        print(f"    Daily high temperature: {weather_inputs[2]:.1f} °C")
        print(f"    Moisture in the air:   {weather_inputs[3]:.1f}% relative humidity")
        print(
            f"    Wind speed:            {weather_inputs[4]:.1f} meters per second ({weather_inputs[4] * 2.236936:.1f} mph)"
        )
        print(f"    Rainfall:              {weather_inputs[5]:.2f} mm per day")
        print("  The time of year is also an input. Future weather is not used.")
    else:
        print(
            "  Required weather readings are missing. We cannot give a risk estimate."
        )
    heading("2. PREDICTION AGENT — estimates the risk")
    result = prediction_agent.predict(collected_data, target_date)
    print(f"  Prediction date: {target_date} (Cedar City local calendar day).")
    if result["status"] == "estimated":
        print(
            f"  Estimated chance of one or more fire reports: {result['probability']:.1%}."
        )
        print("  This chance is for the WHOLE 50-mile area, not your home or one spot.")
        print("  Selected method:", result["model"])
        print("  This method learned a pattern from past fires, weather, and season.")
        print("  A higher percentage means greater estimated risk, not a certain fire.")
    else:
        print("  No estimate shown because required weather information is missing.")
        print("  Missing information does not mean there is no fire risk.")
    heading("3. ALERT AGENT — decides whether to notify you")
    print("  Our project rule: create a risk alert when the estimate is 50% or more.")
    print("  This is a chosen demo rule, not an official firefighting threshold.")
    alert_needed = (
        result.get("status") == "estimated"
        and result["probability"] >= result["threshold"]
    )
    if result["status"] != "estimated":
        print(
            "  Risk decision: no model-based alert decision; the estimate is unavailable."
        )
    elif alert_needed:
        print("  Risk decision: the estimate reaches the alert level.")
    else:
        print("  Risk decision: the estimate is below the alert level.")
        print("  A fire is still possible even when no risk alert is triggered.")
    if options.live:
        print(f"  Official fire reports found: {len(collected_data['incidents'])}.")
        print(
            f"  Relevant or nearby weather-warning records found: {len(collected_data['warnings'])}."
        )
        print(
            "  Only verified local weather warnings and recent qualifying fire reports"
        )
        print("  can create official-update alerts. A warning is not a confirmed fire.")
        existing = {item["id"] for item in alert_agent.history()}
        alert_agent.evaluate(collected_data, result)
        new_alerts = [
            item for item in alert_agent.history() if item["id"] not in existing
        ]
        print(f"  New alerts saved: {len(new_alerts)}. Repeated alerts are skipped.")
        for item in new_alerts:
            print("  ALERT:", item["title"])
            print(" ", item["body"])
            if options.send_email:
                from email_alerts import mail

                email_result(mail(item))
    else:
        print("  This is a past-date demo. No current warning is created or emailed.")
    if not options.live:
        heading("CHECK THE PAST RESULT — only after making the prediction")
        recorded_fire_count = sum(
            (
                pd.to_datetime(f["discovery_date"], unit="ms").date() == target_date
                for f in fire_records
            )
        )
        print(
            f"  Actual recorded fire reports on {target_date}: {recorded_fire_count}."
        )
        if result["status"] != "estimated":
            print("  No estimate was made, so this run cannot be compared.")
        elif alert_needed and recorded_fire_count == 0:
            print("  On this example, the rule would give a FALSE ALARM:")
            print("  it suggested an alert, but no fire was recorded that day.")
        elif alert_needed and recorded_fire_count > 0:
            print("  On this example, the rule correctly suggested an alert.")
        elif not alert_needed and recorded_fire_count > 0:
            print("  On this example, the rule MISSED a day with a recorded fire.")
        else:
            print("  On this example, no alert was suggested and no fire was recorded.")
        print(
            "  One example does not measure the whole model. See the full test below."
        )
    heading("HOW WE TRAINED AND CHECKED THE MODEL")
    print("  2000–2017: teach the models using earlier data.")
    print("  2018–2019: compare models and choose one.")
    print("  2020–2021: adjust the probability estimates.")
    print("  2022–2024: test on later data not used to teach or choose the model.")
    print("  Models compared (smaller prediction-error score is better):")
    for name, value in report["selection_brier"].items():
        print(f"    {name}: {value:.3f}")
    print("  The simple sigmoid model was chosen because it had the lowest")
    print("  comparison error. A more complex neural network did not win here.")
    print("  Class topics: intelligent agents, supervised learning, sigmoid,")
    print("  neural networks with backpropagation, RBF SVM, and separate test data.")
    heading("RESULTS ON ALL FINAL TEST DAYS — 2022–2024")
    correct_no_alert_days, false_alarm_days = report["confusion_matrix_at_0_5"][0]
    missed_fire_days, correct_alert_days = report["confusion_matrix_at_0_5"][1]
    print(f"  Days tested: {report['test_days']:,}.")
    print(f"  Correct alerts on days with a recorded fire: {correct_alert_days}.")
    print(f"  False alarms on days with no recorded fire: {false_alarm_days}.")
    print(f"  Missed days with a recorded fire: {missed_fire_days}.")
    print(
        f"  Correct no-alert decisions on days with no recorded fire: {correct_no_alert_days}."
    )
    print(
        f"  Out of 100 days that triggered an alert, about {report['precision_at_0_5'] * 100:.0f}"
    )
    print("  had a recorded fire. This is called precision.")
    print(
        f"  Out of 100 days with a recorded fire, the rule caught about {report['recall_at_0_5'] * 100:.0f}."
    )
    print("  This is called recall. These are past results, not future guarantees.")
    heading("NOTIFICATIONS AND SAVED FILES")
    from email_alerts import email_status

    status = email_status()
    ready = status["enabled"] and status["configured"]
    print("  Your alert email:", status["recipient"])
    print(
        "  Email setup:",
        "ready" if ready else "not ready — a sending account must be connected.",
    )
    print(
        "  Email on this run:",
        (
            "requested for new live alerts"
            if options.send_email
            else "off (unless you explicitly request a test email)."
        ),
    )
    print("  Fire-department notifications: off.")
    print("  CSV folders: data/US Forest Service, data/NASA, data/Model Data.")
    print("  Detailed model scores: artifacts/metrics.json.")
    print("  Saved local alerts: data/alerts.json.")
    if options.test_alert or options.send_test_email:
        item = alert_agent.emit(
            "test",
            secrets.token_hex(8),
            "Test alert — no wildfire reported",
            "This is a classroom test. It does not report a real fire.",
            True,
        )
        print("  TEST ONLY: a demonstration alert was saved.")
        if options.send_test_email:
            from email_alerts import mail

            email_result(mail(item))
    heading("WHAT THIS PROJECT CANNOT TELL YOU")
    print("  It cannot say exactly where a fire will start or how it will spread.")
    print("  Weather comes from one area; terrain, dry plants, lightning, and")
    print("  human activity are not yet included. Some fires may not be reported.")
    print("  Do not use this student model to make emergency-response decisions.")
    print("\nRun finished. No webpage was started.\n")
    return result


def main(argv=None):
    """Read command-line options and run the requested terminal mode."""
    import contextlib
    import io
    import sys

    arguments = list(sys.argv[1:] if argv is None else argv)
    if any((flag in arguments for flag in ("--details", "--help", "-h"))):
        return run_details(arguments)
    if "--date" not in arguments and (
        not any((flag in arguments for flag in ("--test-alert", "--send-test-email")))
    ):
        from forecast import show_next_three_days

        return show_next_three_days(send_email="--send-email" in arguments)
    live = "--live" in arguments
    print("CEDAR CITY WILDFIRE PREDICTION", flush=True)
    print(f"Area: Cedar City, Utah | {RADIUS}-mile radius")
    print(
        "Mode: "
        + (
            "Live data — checking tomorrow"
            if live
            else "Historical demo — not a current warning"
        ),
        flush=True,
    )
    if live:
        print("Getting weather and fire reports...", flush=True)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = run_details(arguments)
    if result["status"] == "estimated":
        print("Date:", result["target_date"])
        print(
            f"Estimated chance of a fire report in the area: {result['probability']:.1%}"
        )
        print(
            "Risk alert: "
            + (
                "YES — estimate is 50% or higher"
                if result["probability"] >= result["threshold"]
                else "NO — estimate is below 50%"
            )
        )
    else:
        print("Risk estimate: unavailable — required weather readings are missing.")
        print("Risk alert: cannot decide without the missing readings.")
    for line in output.getvalue().splitlines():
        text = line.strip()
        if text.startswith(
            (
                "Actual recorded fire reports",
                "Official fire reports found:",
                "New alerts saved:",
                "TEST ONLY:",
                "ALERT:",
            )
        ):
            print(text)
        elif text.startswith("On this example, the rule would give a FALSE ALARM"):
            print("Historical result: false alarm — no fire was recorded that day.")
        elif text.startswith("On this example, the rule correctly suggested"):
            print("Historical result: alert matched a day with a recorded fire.")
        elif text.startswith("On this example, the rule MISSED"):
            print("Historical result: missed a day with a recorded fire.")
        elif text.startswith("On this example, no alert was suggested"):
            print("Historical result: no alert and no recorded fire.")
        elif text.startswith(
            (
                "The email provider accepted",
                "Email was not sent.",
                "Email could not be sent.",
            )
        ):
            print(text)
    print()
    return result


if __name__ == "__main__":
    main()
