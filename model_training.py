__author__ = "Rahul Rajesh 2360445"

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import OneClassSVM
from sklearn.metrics import classification_report

FEATURES = [
    'qber_overall', 
    'qber_rectilinear', 
    'qber_diagonal',
    'detector_voltage', 
    'timing_jitter', 
    'photon_count_rate'
]

def load_data():
    data_dir = "Datasets/Processed/"
    
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
    
    df = load_data()
    
    print(f"\nTotal Samples (Raw): {len(df)}")
    
    print(" -> Optimization: Downsampling dataset to 25% for faster training...")
    df_sample = df.sample(frac=0.25, random_state=42)
    
    X = df_sample[FEATURES]
    y = df_sample['label']
    
    print(f"Training Samples: {len(df_sample)}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    print("\nTraining Random Forest (Multi-Class Classifier)...")
    
    rf_model = RandomForestClassifier(
        n_estimators=100, 
        min_samples_leaf=10, 
        n_jobs=-1, 
        verbose=0, 
        random_state=42
    )
    rf_model.fit(X_train, y_train)
    
    print("Evaluating Random Forest...")
    y_pred = rf_model.predict(X_test)
    print("Random Forest Performance:")
    print(classification_report(y_test, y_pred))

    print("\nTraining One-Class SVM (Anomaly Detector)...")
    
    X_normal = df[df['label'] == 'normal'][FEATURES]
    
    sample_size = min(50000, len(X_normal))
    X_normal_sample = X_normal.sample(n=sample_size, random_state=42)
    print(f" -> Training SVM on {len(X_normal_sample)} normal samples...")
    
    svm_model = OneClassSVM(kernel='rbf', gamma='scale', nu=0.01)
    svm_model.fit(X_normal_sample)
    
    print("One-Class SVM Trained.")

    os.makedirs("Models", exist_ok=True)
    
    with open("Models/rf_model_v3.pkl", "wb") as f:
        pickle.dump(rf_model, f)
        
    with open("Models/svm_model_v3.pkl", "wb") as f:
        pickle.dump(svm_model, f)
        
    print("\n-> Models saved to 'Models/' folder.")

if __name__ == "__main__":
    train_models()