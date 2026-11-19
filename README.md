# Cedar City Wildfire Prediction — CS 4150

A working class prototype for Cedar City, Utah, and places within 50 miles. Three Python agents collect data, estimate daily risk, and check alerts. Predictions concern a recorded wildfire somewhere in the whole area. They do not predict an exact ignition location or fire spread.

## Start in Google Colab

[Open the working team notebook](https://colab.research.google.com/drive/1HMplOIlgFcRtF-hw6mshQYc8ijwHnO7K). Colab editing access is managed separately by the owner. The included `Cedar_City_Wildfire_Team.ipynb` also contains all code and the public source data: download it and upload it to Colab to run your own copy. Choose **Runtime → Run all**. No separate CSV upload is needed.

## Presentation

Open or download `Cedar_City_Wildfire_Presentation.pptx` for the class slides and short presenter notes. [Google Slides version](https://docs.google.com/presentation/d/1980g4HVvmKXHoqzvYWvujJmoJe7FFtCZlJMGQ7_YMYc/edit).

## Run locally

Download `CedarFire_Complete_Project.zip` and extract it first. The ZIP preserves all data folders and tests. The Python files at the repository root are also available for easy reading; use the ZIP for the complete local project.

From the extracted project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python train.py
python main.py --date 2024-07-01
python main.py
python -m unittest discover -s tests -v
```

On Windows, activate with `.venv\Scripts\activate` instead. Train once before predicting so the saved model matches your library versions. The historical example works without live requests; the normal three-day run needs internet. To edit code in Colab, edit its `%%writefile` cell, rerun it, then rerun training or the demo.

## What is included

- `core.py`: DataAgent, PredictionAgent, AlertAgent.
- `train.py`: compares Logistic Regression, Multi-Layer Perceptron (MLP), and Support Vector Machine (SVM) with a Radial Basis Function (RBF) kernel.
- `main.py`, `demo.py`, `forecast.py`: terminal results and daily risk estimates.
- The complete ZIP includes source-named CSV folders: `data/US Forest Service`, `data/NASA`, and `data/Model Data`, plus original agency downloads, project guides, and nine tests.
- The notebook bundles the same public data and can restore it in a new Colab runtime.

## Data and model

There are 6,272 recorded fires, 9,132 weather days, and 9,118 daily model examples. Training uses 2000–2017, selection 2018–2019, calibration 2020–2021, and final testing 2022–2024. Six inputs describe season and older weather. For target T, weather is averaged from T−14 through T−8.

The original selected model is Logistic Regression. On the 1,096-day historical test, precision is 56.3% and recall is 70.5% at a chosen 50% alert threshold. Different library versions may slightly change retrained results. The original reference report is included in the ZIP.

## Sources

- [US Forest Service FPA FOD, seventh edition](https://doi.org/10.2737/RDS-2013-0009.7)
- [NASA POWER daily weather](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
- [National Interagency Fire Center](https://data-nifc.opendata.arcgis.com/)

Presentation theme: [SlidesCarnival Salisbury / Magical Forest](https://www.slidescarnival.com/template/salisbury-free-presentation-template/12314), forest artwork by Alex Monge. Example wildfire photo: Getty Images, inserted through Google Slides stock images. The photo does not show a claimed Cedar City incident.

## Limits and alerts

This is an academic prototype, not an official warning or emergency dispatch system. Weather is from one central point, and fuels, terrain, lightning, and human activity are not included. Three-day estimates reuse the daily model; each forecast horizon needs more testing. Missing data is not an all-clear.

Email is disabled by default, and no passwords or local environment files are included. Sender setup and real delivery testing are still needed. Fire departments are not contacted. Never commit credentials to GitHub or a shared notebook.
