"""
explain_models.py
Phase 4: XAI Explanation — SHAP global visualisations.
Generates summary (bar) and beeswarm (dot) SHAP plots for each attack class,
saved as high-resolution PNG forensic evidence.
"""
__author__ = "Rahul Rajesh 2360445"

import pandas as pd
import numpy as np
import pickle
import shap
import matplotlib.pyplot as plt
import os

from config.logging_config import configure_logging, get_logger

configure_logging()
log = get_logger("qkd.xai")

FEATURES: list[str] = [
    'qber_overall',
    'qber_rectilinear',
    'qber_diagonal',
    'detector_voltage',
    'timing_jitter',
    'photon_count_rate',
]

RESULTS_DIR = "Results/Forensic_Evidence"


def explain_predictions() -> None:
    """
    Load the trained Random Forest, compute SHAP values for each attack class,
    and save global bar + beeswarm plots to Results/Forensic_Evidence/.
    """
    log.info("--- Phase 4: XAI Explanation (High-Res & Organised) ---")

    model_path = "Models/rf_model_v3.pkl"
    if not os.path.exists(model_path):
        log.error("Model not found at '%s'. Run model_training.py first.", model_path)
        return

    with open(model_path, "rb") as f:
        rf_model = pickle.load(f)

    log.info("Initialising SHAP TreeExplainer...")
    explainer = shap.TreeExplainer(rf_model)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    log.info(f"Saving all evidence to: {RESULTS_DIR}/")

    def generate_plot(attack_name: str, csv_filename: str, clean_name: str) -> None:
        """Compute and save SHAP bar + beeswarm plots for one attack class."""
        log.info(f"Explaining '{attack_name}'...")
        data_path = f"Datasets/Processed/{csv_filename}"

        if not os.path.exists(data_path):
            log.warning(f"Skipping '{attack_name}' — '{data_path}' not found.")
            return

        df = pd.read_csv(data_path)
        X_sample = df[FEATURES].sample(n=100, random_state=42)

        log.debug(f"  Calculating SHAP values for {len(X_sample)} samples...")
        shap_values = explainer.shap_values(X_sample, check_additivity=False)

        class_names = rf_model.classes_
        try:
            target_index = np.where(class_names == attack_name)[0][0]
        except IndexError:
            log.error(f"Class '{attack_name}' not found in model classes: {class_names.tolist()}")
            return

        # Resolve SHAP value format across scikit-learn versions
        shap_values_target: np.ndarray
        if isinstance(shap_values, list):
            shap_values_target = shap_values[target_index]
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            if shap_values.shape[0] == len(X_sample):
                shap_values_target = shap_values[:, :, target_index]
            else:
                shap_values_target = shap_values[target_index]
        else:
            shap_values_target = shap_values[target_index]

        # ---- Bar plot (global feature importance) ----
        plt.figure(figsize=(10, 6))
        shap.summary_plot(
            shap_values_target,
            X_sample,
            feature_names=FEATURES,
            show=False,
            plot_type="bar",
        )
        plt.title(f"Primary Indicators: {clean_name}", fontsize=14)
        plt.tight_layout()
        bar_path = os.path.join(RESULTS_DIR, f"Evidence_{clean_name}_Summary.png")
        plt.savefig(bar_path, dpi=300, bbox_inches='tight')
        plt.close()
        log.info(f"  Saved summary bar plot: '{bar_path}'")

        # ---- Beeswarm plot (per-sample SHAP magnitudes) ----
        plt.figure(figsize=(12, 8))
        shap.summary_plot(
            shap_values_target,
            X_sample,
            feature_names=FEATURES,
            show=False,
            plot_type="dot",
        )
        plt.title(f"Forensic Fingerprint: {clean_name}", fontsize=14)
        plt.tight_layout()
        dot_path = os.path.join(RESULTS_DIR, f"Evidence_{clean_name}_Detailed.png")
        plt.savefig(dot_path, dpi=300, bbox_inches='tight')
        plt.close()
        log.info(f"  Saved beeswarm plot:   '{dot_path}'")

    generate_plot("attack_timeshift", "attack_timeshift.csv", "TimeShift_Attack")
    generate_plot("attack_blinding",  "attack_blinding.csv",  "Blinding_Attack")

    log.info("--- XAI Generation Complete ---")


if __name__ == "__main__":
    explain_predictions()