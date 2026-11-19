"""Run locally to configure your sender. Password input is hidden."""

import getpass
import os
from pathlib import Path

project_folder = Path(__file__).resolve().parent
print("Cedar Fire email setup → your_email@example.com")
print("Use a Gmail app password for your sending account. Do not paste it into chat.")
sender_email = input("Sending Gmail address: ").strip()
if not sender_email.endswith("@gmail.com") or "\n" in sender_email:
    raise SystemExit("Use a Gmail sender address for this prototype.")
# getpass hides the password while the user types it in their own terminal.
app_password = getpass.getpass("Gmail app password (hidden): ").replace(" ", "")
if len(app_password) != 16 or not app_password.isalnum():
    raise SystemExit(
        "Expected a 16-character Google app password; configuration was not saved."
    )
settings_file = project_folder / ".env"
# Only the current user may read or write the saved password file.
file_handle = os.open(settings_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 384)
with os.fdopen(file_handle, "w") as settings_output:
    settings_output.write(
        f"EMAIL_ENABLED=true\nSMTP_HOST=smtp.gmail.com\nSMTP_PORT=465\nSMTP_USER={sender_email}\nSMTP_PASSWORD={app_password}\n"
    )
os.chmod(settings_file, 384)
print("Saved local .env. Run: .venv/bin/python main.py --send-test-email")
print(
    "The terminal prints the sending result; also check your Gmail inbox/spam folder."
)
