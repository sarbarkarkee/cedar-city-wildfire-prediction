# Read the project in this order

1. **main.py** — starts the program and reads terminal options.
2. **forecast.py** — runs the three-day prediction and prints the short results table.
3. **core.py** — contains the three agents and shared weather/distance calculations.
4. **train.py** — trains the sigmoid classifier, neural network, and RBF SVM; compares them; saves the selected model.
5. **export_data.py** — creates the CSV files from downloaded agency data.
6. **download.py** — downloads official historical fire reports.
7. **email_alerts.py** — sends an alert only when email is explicitly enabled.
8. **setup_email.py** — stores the sender settings locally without printing the password.

`demo.py` supports historical demonstrations and the optional detailed mode. `app.py` only forwards to the terminal program; it does not start a website.

## Names used in the code

- `target_date`: the day we want to predict.
- `weather_table`: daily NASA weather readings.
- `input_values`: numbers supplied to the classifier.
- `fire_labels`: 1 when a fire was recorded that day, otherwise 0.
- `fire_probability`: the model's estimated chance of a reported wildfire.
- `training_days`, `selection_days`, `calibration_days`, `test_days`: separate groups of dates.
- `saved_alerts`: alerts already recorded, used to avoid duplicates.

`np` means NumPy, `pd` means pandas, and `dt` means Python's datetime library. These conventional library aliases are kept so examples match common Python documentation.

Comments explain the reason for each important step. Agency field names and saved model keys are unchanged so the real data and trained model remain compatible.
