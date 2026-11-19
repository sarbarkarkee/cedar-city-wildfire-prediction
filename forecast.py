"""Show three daily regional risk estimates using the saved model and official data."""

import datetime as dt
import json
from core import ROOT, RADIUS, TZ, now, DataAgent, PredictionAgent, AlertAgent


def show_next_three_days(send_email=False):
    """Run the three agents and print one short result row for each day."""
    # Tomorrow is based on Cedar City time, not the computer server's timezone.
    first_date = dt.datetime.now(TZ).date() + dt.timedelta(days=1)
    print("CEDAR CITY, UTAH | WILDFIRE RISK", flush=True)
    print(f"Area: within {RADIUS} miles of Cedar City")
    print("Getting recent weather data...", flush=True)
    # Collect once, then reuse the readings for all three target dates.
    collected_data = DataAgent().collect(first_date, forecast_days=3)
    prediction_agent = PredictionAgent()
    alert_agent = AlertAgent()
    predictions = []
    old_alert_ids = {saved_alert["id"] for saved_alert in alert_agent.history()}
    print("\nDate          Chance of a fire report    Risk alert")
    print("--------------------------------------------------")
    # Predict each day separately; do not reuse one probability for all days.
    for day_number in range(3):
        target_date = first_date + dt.timedelta(days=day_number)
        daily_weather = collected_data.get("weather_horizon", {}).get(
            target_date.isoformat()
        )
        daily_data = {**collected_data, "weather": daily_weather}
        daily_prediction = prediction_agent.predict(daily_data, target_date)
        predictions.append(daily_prediction)
        # Missing inputs remain unavailable instead of being filled with fake readings.
        if daily_prediction["status"] == "estimated":
            chance_text = f"{daily_prediction['probability']:.1%}"
            alert_text = (
                "YES"
                if daily_prediction["probability"] >= daily_prediction["threshold"]
                else "NO"
            )
        else:
            chance_text = "Unavailable"
            alert_text = "Cannot decide"
        print(f"{target_date.isoformat()}    {chance_text:<26}{alert_text}")
        if daily_prediction["status"] == "estimated":
            alert_agent.evaluate(daily_data, daily_prediction)
    print("\nRisk alert level: 50% or higher.")
    print("Chance refers to any reported wildfire in the whole area, not one location.")
    print("Estimates use past weather and season; they are not official fire warnings.")
    if any(
        (saved_prediction["status"] != "estimated" for saved_prediction in predictions)
    ):
        print(
            "Some required weather readings could not be obtained. No replacement values were used."
        )
    # Email is optional. Send only alerts created during this run.
    if send_email:
        from email_alerts import mail

        new_alerts = [
            saved_alert
            for saved_alert in alert_agent.history()
            if saved_alert["id"] not in old_alert_ids
        ]
        for saved_alert in new_alerts:
            email_status = mail(saved_alert)["status"]
            print(
                "Email:",
                (
                    "accepted by provider"
                    if email_status == "accepted_by_smtp"
                    else "not sent — check sender setup"
                ),
            )
        if not new_alerts:
            print("Email: no new alerts to send.")
    else:
        print("Email: not sent.")
    # Save the latest results so the group can inspect them after the terminal run.
    (ROOT / "data/three_day_results.json").write_text(
        json.dumps(
            {
                "created_at": now().isoformat(),
                "radius_miles": RADIUS,
                "predictions": predictions,
            },
            indent=2,
        )
    )
    print()
    return predictions
