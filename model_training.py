import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import OneClassSVM
from sklearn.metrics import classification_report

# --- CONFIGURATION ---
# The exact 6 features used in v3.0
FEATURES = [
    'qber_overall', 
    'qber_rectilinear', 
    'qber_diagonal',
    'detector_voltage', 
    'timing_jitter', 
    'photon_count_rate'
]

def load_data():
    """
    Loads all 4 processed datasets and combines them into one training set.
    """
    data_dir = "Datasets/Processed/"
    
    # Map filenames to expected labels
    files = {
        "normal_data.csv": "normal",
        "attack_intercept.csv": "attack_intercept",
        "attack_blinding.csv": "attack_blinding",
        "attack_timeshift.csv": "attack_timeshift"
    }
    
    dfs = []
    print("Loading datasets...")
    for filename, label_name in files.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            df = pd.read_csv(path)
            # Ensure the label column is correct
            df['label'] = label_name
            dfs.append(df)
            print(f" -> Loaded {filename}: {len(df)} rows")
        else:
            print(f"Warning: {filename} not found! Skipping.")
            
    if not dfs:
        raise ValueError("No data found! Run data_preprocessing.py first.")
        
    full_df = pd.concat(dfs, ignore_index=True)
    return full_df

def train_models():
    print("\n--- Phase 3: Model Training (v3.0) ---")
    
    # 1. Load Data
    df = load_data()
    
    print(f"\nTotal Samples (Raw): {len(df)}")
    
    # --- OPTIMIZATION: Downsample for Speed ---
    # 4 Million rows is overkill for a prototype. 
    # We train on a random 25% (1 Million rows). It's still huge but 4x faster.
    print(" -> Optimization: Downsampling dataset to 25% for faster training...")
    df_sample = df.sample(frac=0.25, random_state=42)
    
    X = df_sample[FEATURES]
    y = df_sample['label']
    
    print(f"Training Samples: {len(df_sample)}")

    # 2. Train-Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    # --- MODEL 1: THE "EXPERT" (Random Forest) ---
    print("\nTraining Random Forest (Multi-Class Classifier)...")
    
    # UPDATED: n_jobs=-1 uses ALL cores. verbose=2 shows progress.
    # Change from default to a more robust leaf size
    rf_model = RandomForestClassifier(
        n_estimators=100, 
        min_samples_leaf=10, # Add this to prevent over-fitting to specific QBER values
        n_jobs=-1, 
        verbose=2, 
        random_state=42
    )
    rf_model.fit(X_train, y_train)
    
    # Evaluate
    print("Evaluating Random Forest...")
    y_pred = rf_model.predict(X_test)
    print("Random Forest Performance:")
    print(classification_report(y_test, y_pred))

    # --- MODEL 2: THE "GUARD" (One-Class SVM) ---
    print("\nTraining One-Class SVM (Anomaly Detector)...")
    
    # We only train OCSVM on NORMAL data
    # Note: We go back to the original full dataframe to find normal data, 
    # then sample it freshly to ensure we get a good distribution.
    X_normal = df[df['label'] == 'normal'][FEATURES]
    
    # 50,000 samples is a good balance for speed/accuracy for SVM
    sample_size = min(50000, len(X_normal))
    X_normal_sample = X_normal.sample(n=sample_size, random_state=42)
    print(f" -> Training SVM on {len(X_normal_sample)} normal samples...")
    
    svm_model = OneClassSVM(kernel='rbf', gamma='scale', nu=0.01)
    svm_model.fit(X_normal_sample)
    
    print("One-Class SVM Trained.")

    # 3. Save Models
    os.makedirs("Models", exist_ok=True)
    
    with open("Models/rf_model_v3.pkl", "wb") as f:
        pickle.dump(rf_model, f)
        
    with open("Models/svm_model_v3.pkl", "wb") as f:
        pickle.dump(svm_model, f)
        
    print("\n-> Models saved to 'Models/' folder.")

if __name__ == "__main__":
    train_models()