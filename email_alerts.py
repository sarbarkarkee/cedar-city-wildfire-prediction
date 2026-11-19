"""Email delivery for the terminal project. No web server or model is loaded here."""

import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from core import ROOT, now, AlertAgent

# Read sender settings locally. Never print or commit the app password.
if (ROOT / ".env").exists():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip() and (not line.lstrip().startswith("#")) and ("=" in line):
            setting_name, setting_value = line.split("=", 1)
            os.environ.setdefault(
                setting_name.strip(), setting_value.strip().strip('"').strip("'")
            )
RECIPIENT = os.getenv("ALERT_RECIPIENT", "")


def email_status():
    """Check local email settings without showing any password."""
    return {
        "recipient": RECIPIENT,
        "configured": bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD")),
        "enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
        "department_delivery": "disabled",
    }


def mail(alert):
    """Send one alert by email and save whether the provider accepted it."""
    alert_agent = AlertAgent()
    email_settings = email_status()
    if not email_settings["enabled"] or not email_settings["configured"]:
        return {
            "status": "not_sent",
            "reason": "Email credentials or EMAIL_ENABLED are not configured",
        }
    # Keep the recipient fixed to the project owner; departments are not contacted.
    message = EmailMessage()
    message["From"] = os.environ["SMTP_USER"]
    message["To"] = RECIPIENT
    message["Subject"] = (
        "[TEST] " if alert.get("test") else "[CEDAR FIRE PROTOTYPE] "
    ) + alert["title"]
    message["Message-ID"] = f"<{alert['id']}@cedar-fire.local>"
    message.set_content(
        alert["body"]
        + "\n\nAcademic prototype — not an official warning or emergency dispatch.\n50-mile radius of Cedar City, Utah. Verify official NWS/NIFC information.\nAlert ID: "
        + alert["id"]
    )
    # TLS encrypts the SMTP connection and verifies the mail server certificate.
    try:
        with smtplib.SMTP_SSL(
            os.getenv("SMTP_HOST", "smtp.gmail.com"),
            int(os.getenv("SMTP_PORT", "465")),
            context=ssl.create_default_context(),
            timeout=25,
        ) as email_server:
            email_server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            email_server.send_message(message)
        result = {
            "status": "accepted_by_smtp",
            "at": now().isoformat(),
            "recipient": RECIPIENT,
        }
    except Exception as error:
        result = {
            "status": "failed",
            "reason": type(error).__name__ + " — check local sender configuration",
        }
    # Provider acceptance is recorded; it is not proof of inbox delivery.
    with alert_agent.lock:
        saved_alerts = alert_agent.history()
        for saved_alert in saved_alerts:
            if saved_alert["id"] == alert["id"]:
                saved_alert["email"] = result
        alert_agent.path.write_text(json.dumps(saved_alerts, indent=2))
    return result
