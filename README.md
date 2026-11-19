# Cedar City Wildfire Prediction

CS 4150 class project. The program estimates the chance of a wildfire being reported within 50 miles of Cedar City, Utah, for the next three days. Results appear in the terminal.

## What each Python file does

| File | What it does |
| --- | --- |
| `main.py` | Starts the program. Use this file to run predictions, view saved alerts, or repeat checks. |
| `core.py` | Contains the three agents. The Data Agent gets weather and official fire information. The Prediction Agent estimates fire risk. The Alert Agent checks whether an alert is needed and saves it. It also has shared calculations used by the other files. |
| `forecast.py` | Gets recent data and shows a separate risk estimate for each of the next three days. It saves the results and can send new alerts when email is enabled. |
| `train.py` | Teaches the models using past fire and weather data. It compares Logistic Regression, a Multi-Layer Perceptron (MLP), and a Support Vector Machine (SVM), chooses a model, tests it, and saves it. |
| `demo.py` | Runs the classroom examples. It can show a prediction for a past date, compare it with recorded fires, and create a local test alert. It also connects the main program to the three-day forecast. |
| `download.py` | Downloads past fire reports from the United States Forest Service (USFS). It keeps reports within 50 miles of Cedar City. The project ZIP already includes the downloaded data. |
| `export_data.py` | Converts the downloaded data into comma-separated values (CSV) files that are easy to open. It puts fire, weather, and model data into separate folders. |
| `email_alerts.py` | Checks the email settings and sends alerts using Simple Mail Transfer Protocol (SMTP) when enabled. It records whether the email provider accepted the message. Email is off until a sender is configured. |
| `tests/test_core.py` (inside the ZIP) | Checks important calculations and agent behavior to help catch errors. |

## Download and run

Download **CedarFire_Complete_Project.zip** and extract it. Open the **CedarFire-CS4150** folder in Visual Studio Code (VS Code). The ZIP includes the code, data folders, and tests. Download the presentation separately from **Cedar_City_Wildfire_Presentation.pptx**.

In the project terminal, install the libraries and train the model once:

```bash
python -m pip install -r requirements.txt
python train.py
```

Show the next three days (internet needed):

```bash
python main.py
```

Show a past example using the included data:

```bash
python main.py --date 2024-07-01
```

Some computers use `python3` instead of `python`. `requirements.txt` lists the libraries the project needs.

This is a student prototype. The estimate is for the whole area, not an exact fire location. It is not an official fire warning. Fire departments are not contacted.
