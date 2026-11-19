"""Train and compare the wildfire classifiers taught in CS 4150."""

import json
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    brier_score_loss,
    precision_score,
    recall_score,
    confusion_matrix,
)
from core import ROOT, features, weather_frame, score


def train_models():
    """Read data, compare classifiers, evaluate, and save the selected model."""
    warnings.filterwarnings("ignore", category=UserWarning)
    # 1. Read actual agency downloads. No synthetic labels are used.
    fire_records = json.loads((ROOT / "data/fires.json").read_text())
    weather_table = weather_frame(
        json.loads((ROOT / "data/weather_history.json").read_text())
    )
    target_dates = pd.date_range("2000-01-15", "2024-12-31")
    input_values = features(target_dates, weather_table)
    fire_dates = {
        pd.to_datetime(fire_record["discovery_date"], unit="ms").normalize()
        for fire_record in fire_records
    }
    # Label 1 means at least one recorded discovery that day; otherwise label 0.
    fire_labels = np.array(
        [int(target_date in fire_dates) for target_date in target_dates]
    )
    # Drop days with missing weather rather than inventing replacement readings.
    has_all_weather = np.isfinite(input_values).all(axis=1)
    input_values = input_values[has_all_weather]
    fire_labels = fire_labels[has_all_weather]
    target_dates = target_dates[has_all_weather]
    # 2. Split by year, keeping later test years separate from learning.
    training_days = target_dates.year <= 2017
    selection_days = (target_dates.year >= 2018) & (target_dates.year <= 2019)
    calibration_days = (target_dates.year >= 2020) & (target_dates.year <= 2021)
    test_days = target_dates.year >= 2022
    # 3. Compare the class methods: sigmoid baseline, neural network, and RBF SVM.
    # The MLP uses sigmoid hidden units, backpropagation, and L2 regularization.
    candidate_models = {
        "Sigmoid logistic baseline": LogisticRegression(max_iter=1000),
        "MLP · 12 → 6 → sigmoid": MLPClassifier(
            hidden_layer_sizes=(12, 6),
            activation="logistic",
            alpha=0.1,
            max_iter=500,
            random_state=4150,
        ),
        "SVM · RBF kernel": SVC(C=1, kernel="rbf", probability=True, random_state=4150),
    }
    trained_models = {}
    comparison_scores = {}
    for model_name, classifier in candidate_models.items():
        # Learn scaling from training rows only to avoid leaking later information.
        trained_model = make_pipeline(StandardScaler(), classifier)
        trained_model.fit(input_values[training_days], fire_labels[training_days])
        comparison_scores[model_name] = float(
            brier_score_loss(
                fire_labels[selection_days],
                trained_model.predict_proba(input_values[selection_days])[:, 1],
            )
        )
        trained_models[model_name] = trained_model
        print(model_name, comparison_scores[model_name], flush=True)
    # 4. Choose using selection years only. Lower Brier score means lower error.
    model_name = min(comparison_scores, key=comparison_scores.get)
    trained_model = trained_models[model_name]
    # 5. Adjust probabilities on separate calibration years, not the final test years.
    probability_adjuster = LogisticRegression(C=1000.0).fit(
        score(trained_model, input_values[calibration_days]),
        fire_labels[calibration_days],
    )
    # 6. Evaluate the chosen, adjusted model on untouched later test dates.
    test_probabilities = probability_adjuster.predict_proba(
        score(trained_model, input_values[test_days])
    )[:, 1]
    training_fire_rate = float(fire_labels[training_days].mean())
    report = {
        "target": "regional recorded discovery day, 50-mile circle",
        "training": "2000–2017",
        "selection": "2018–2019",
        "calibration": "2020–2021",
        "untouched_test": "2022–2024",
        "selection_brier": comparison_scores,
        "selected_model": model_name,
        "records": len(fire_records),
        "samples": int(len(fire_labels)),
        "features": [
            "day-of-year sine",
            "day-of-year cosine",
            "lagged 7-day temperature mean (C)",
            "lagged 7-day humidity mean (%)",
            "lagged 7-day wind mean (m/s)",
            "lagged 7-day precipitation mean (mm/day)",
        ],
        "weather_window": "For target T, average UTC daily observations T-14 through T-8, inclusive; center-point coarse weather only.",
        "test_days": int(test_days.sum()),
        "test_prevalence": float(fire_labels[test_days].mean()),
        "average_precision": float(
            average_precision_score(fire_labels[test_days], test_probabilities)
        ),
        "roc_auc": float(roc_auc_score(fire_labels[test_days], test_probabilities)),
        "brier": float(brier_score_loss(fire_labels[test_days], test_probabilities)),
        "constant_baseline_brier": float(
            brier_score_loss(
                fire_labels[test_days], np.full(test_days.sum(), training_fire_rate)
            )
        ),
        "precision_at_0_5": float(
            precision_score(
                fire_labels[test_days], test_probabilities >= 0.5, zero_division=0
            )
        ),
        "recall_at_0_5": float(
            recall_score(
                fire_labels[test_days], test_probabilities >= 0.5, zero_division=0
            )
        ),
        "confusion_matrix_at_0_5": confusion_matrix(
            fire_labels[test_days], test_probabilities >= 0.5
        ).tolist(),
        "limitations": [
            "Retrospective reanalysis availability is assumed at a conservative 7-day lag; this is not a historical forecast replay.",
            "No fuels, lightning, terrain or human ignition inputs. Center-point weather cannot represent the full 50-mile area.",
            "Discovery dates may differ from ignition dates and records are incomplete. Unrecorded-fire days are treated as negative.",
            "Chronological regional test only; no spatial or prospective operational validation.",
            "Current inference is beyond historical training years. Probability is experimental.",
            "Risk is for any discovery anywhere in the region, not at a specific map point.",
        ],
    }
    # 7. Save the model, its probability adjustment, and the test report together.
    joblib.dump(
        {
            "model": trained_model,
            "calibrator": probability_adjuster,
            "name": model_name,
            "report": report,
        },
        ROOT / "artifacts/model.joblib",
    )
    (ROOT / "artifacts/metrics.json").write_text(json.dumps(report, indent=2))
    (ROOT / "data/Model Data").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": target_dates[test_days].strftime("%Y-%m-%d"),
            "observed": fire_labels[test_days],
            "probability": test_probabilities,
        }
    ).to_csv(ROOT / "data/Model Data/test_predictions.csv", index=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    train_models()
