import pandas as pd
import numpy as np
import joblib
import os
import shap
import lime
import lime.lime_tabular
import matplotlib.pyplot as plt

# Project configuration
DATA_PATH = "Datasets/Processed/"
MODEL_PATH = "Models/"
RESULTS_PATH = "Results/"

# Create results directory if it doesn't exist
os.makedirs(RESULTS_PATH, exist_ok=True)

def load_artifacts():
    """
    Load the processed datasets and the pre-trained models from disk.
    """
    print("Loading artifacts...")
    
    # Load datasets
    df_normal = pd.read_csv(os.path.join(DATA_PATH, "normal_data.csv"))
    df_attack = pd.read_csv(os.path.join(DATA_PATH, "attack_intercept.csv"))
    
    # Load trained models
    rf_model = joblib.load(os.path.join(MODEL_PATH, "random_forest.pkl"))
    svm_model = joblib.load(os.path.join(MODEL_PATH, "one_class_svm.pkl"))
    
    return df_normal, df_attack, rf_model, svm_model

def generate_shap_explanations(model, df_normal, df_attack):
    """
    Generate SHAP plots for the Random Forest Classifier.
    """
    print("\n[SHAP] Generating explanations for Random Forest...")
    
    features = ['qber_rolling', 'basis_match', 'error']
    
    # Create background dataset
    background_data = pd.concat([df_normal[features].sample(50), df_attack[features].sample(50)])
    
    explainer = shap.TreeExplainer(model)
    
    # --- 1. Global Feature Importance ---
    print(" -> Generating Summary Plot...")
    
    # Calculate SHAP values for a larger summary set
    summary_data = pd.concat([df_normal[features].sample(100), df_attack[features].sample(100)])
    shap_values = explainer.shap_values(summary_data)
    
    # --- FIX: Handle different SHAP return types (List vs Array) ---
    if isinstance(shap_values, list):
        # Old SHAP: Returns list [Class0, Class1]
        attack_shap_values = shap_values[1]
    elif len(np.array(shap_values).shape) == 3:
        # New SHAP: Returns array (Samples, Features, Classes)
        attack_shap_values = shap_values[:, :, 1]
    else:
        # Fallback (Binary model returning single matrix)
        attack_shap_values = shap_values

    plt.figure()
    shap.summary_plot(attack_shap_values, summary_data, show=False)
    plt.savefig(os.path.join(RESULTS_PATH, "shap_global_importance.png"), bbox_inches='tight')
    plt.close()
    print(" -> Saved: Results/shap_global_importance.png")

    # --- 2. Local Explanation (Force Plot) ---
    print(" -> Generating Attack Explanation...")
    
    # Select a high-confidence attack sample (keep as DataFrame for shape consistency)
    attack_sample = df_attack[df_attack['qber_rolling'] > 0.20][features].iloc[[0]]
    
    # Calculate SHAP values for this single instance
    single_shap_values = explainer.shap_values(attack_sample)
    
    # Fix for single instance slicing
    if isinstance(single_shap_values, list):
        single_val_plot = single_shap_values[1][0]
    elif len(np.array(single_shap_values).shape) == 3:
        single_val_plot = single_shap_values[0, :, 1]
    else:
        single_val_plot = single_shap_values[0]

    # Generate force plot
    p = shap.force_plot(
        explainer.expected_value[1], 
        single_val_plot, 
        attack_sample.iloc[0], 
        matplotlib=True, 
        show=False
    )
    plt.savefig(os.path.join(RESULTS_PATH, "shap_single_attack.png"), bbox_inches='tight')
    plt.close()
    print(" -> Saved: Results/shap_single_attack.png")

def generate_lime_explanations(model, df_normal, df_attack):
    """
    Generate LIME explanation for the One-Class SVM.
    """
    print("\n[LIME] Generating explanations for One-Class SVM...")
    
    features = ['qber_rolling', 'basis_match', 'error']
    
    # LIME needs training data statistics
    X_train_summary = df_normal[features].sample(1000).values
    
    explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=X_train_summary,
        feature_names=features,
        class_names=['Normal', 'Anomaly'], 
        mode='classification'
    )
    
    def svm_predict_proba(data):
        decision = model.decision_function(data)
        proba_normal = 1 / (1 + np.exp(-decision)) 
        return np.column_stack([proba_normal, 1 - proba_normal])

    # Select an anomaly instance
    attack_sample = df_attack[df_attack['qber_rolling'] > 0.20][features].iloc[0].values
    
    print(" -> Explaining a detected anomaly...")
    try:
        exp = explainer.explain_instance(
            attack_sample, 
            svm_predict_proba, 
            num_features=3
        )
        exp.save_to_file(os.path.join(RESULTS_PATH, "lime_svm_explanation.html"))
        print(" -> Saved: Results/lime_svm_explanation.html")
    except Exception as e:
        print(f"LIME Error (skipping plot): {e}")

def main():
    df_normal, df_attack, rf_model, svm_model = load_artifacts()
    
    generate_shap_explanations(rf_model, df_normal, df_attack)
    generate_lime_explanations(svm_model, df_normal, df_attack)
    
    print("\n--- XAI Generation Complete ---")

if __name__ == "__main__":
    main()