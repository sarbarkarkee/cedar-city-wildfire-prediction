# Present the model in VS Code — no website needed

Open the folder `cedar-fire` in VS Code. Open **Terminal → New Terminal**. The Python environment is already connected on this computer.

## 1. Run the offline demonstration

```sh
.venv/bin/python main.py
```

This loads real downloaded data, predicts for a held-out historical day, checks what was reported, and explains the alert decision. It works without internet and does not send an email or report a real-time emergency.

Choose another held-out date:

```sh
.venv/bin/python main.py --date 2023-08-01
```

## 2. Show the CSV data

Open `data/US Forest Service/fire_history_50_miles.csv`, `data/NASA/weather_history.csv`, and `data/Model Data/training_data.csv` in the Explorer. See `data/DATA_GUIDE.md` for column meanings and sources.

## 3. Show the three agents in core.py

- DataAgent gathers and checks official data.
- PredictionAgent runs the trained classifier.
- AlertAgent applies the risk threshold and prevents duplicate alerts.

Explain that agents are Python classes with separate responsibilities. They do not require an LLM or paid service.

## 4. Train the models in front of the class

```sh
.venv/bin/python train.py
```

Compare the sigmoid baseline, sigmoid neural network, and RBF SVM. Show the different year ranges for training, model selection, probability adjustment, and testing. Explain why the simpler model won. See `artifacts/metrics.json` for exact scores.

## 5. Run live prediction (internet needed)

```sh
.venv/bin/python main.py --live
```

Fetch official current data and print the next-day estimate. A missing required weather input means the estimate is withheld, not replaced with fake weather. Live runs can save current alerts locally; email is not sent by this command.

## 6. Demonstrate alerts

```sh
.venv/bin/python main.py --test-alert
```

This saves a clearly labeled local test alert. It does not email anyone.

To email a test to your_email@example.com, first configure a sending account locally using the README instructions, then run:

```sh
.venv/bin/python setup_email.py
.venv/bin/python main.py --send-test-email
```

Do not put passwords in code or paste them into chat. No email credentials were supplied during project creation, so real delivery remains unverified.

## Files to explain

1. `export_data.py`: convert the official downloads into readable CSVs.
2. `train.py`: prepare labels and train/compare models.
3. `core.py`: the three agents and feature calculations.
4. `main.py`: the terminal-only presentation.
5. `artifacts/metrics.json`: saved evaluation results.

## Honest conclusion

This prototype estimates the chance of at least one reported wildfire somewhere within 50 miles of Cedar City on the next local calendar day. It cannot name the exact ignition point or predict fire spread. Past test results do not guarantee future performance.

## Reinstall on another computer

The local `.venv` is linked to the environment prepared on this computer. On a different computer, create a fresh environment and install the included requirements:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```
