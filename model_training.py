import pandas as pd
import numpy as np
import joblib
import os
import time
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import OneClassSVM
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# --- CONFIGURATION ---
# We look for the "Textbooks" (Processed Data) here
DATA_PATH = "Datasets/Processed/"
# We save the "Brains" (Trained Models) here
MODEL_PATH = "Models/"
RESULTS_PATH = "Results/"

# Ensure output directories exist
os.makedirs(MODEL_PATH, exist_ok=True)
os.makedirs(RESULTS_PATH, exist_ok=True)

def load_data():
    print("Loading datasets...")
    # 1. Load the "Safe" Textbook (Label = 0)
    df_normal = pd.read_csv(os.path.join(DATA_PATH, "normal_data.csv"))
    df_normal['label_code'] = 0  
    
    # 2. Load the "Attack" Textbook (Label = 1)
    df_attack = pd.read_csv(os.path.join(DATA_PATH, "attack_intercept.csv"))
    df_attack['label_code'] = 1
    
    print(f" -> Loaded {len(df_normal)} Normal rows and {len(df_attack)} Attack rows.")
    return df_normal, df_attack

def train_one_class_svm(df_normal, df_attack):
    print("\n--- Training Model 1: One-Class SVM (Anomaly Detection) ---")
    print("(Concept: 'I only know what Normal looks like. Anything else is a threat.')")
    
    features = ['qber_rolling', 'basis_match', 'error']
    
    # --- TRAIN ---
    # We train ONLY on Normal data.
    # 100,000 samples is the "Sweet Spot" for SVM precision vs. time.
    print(" -> Preparing Training Data (100k Normal samples)...")
    X_train = df_normal[features].sample(n=100000, random_state=42)
    
    print(" -> Training Start (This may take 1-3 minutes)...")
    start_time = time.time()
    
    # nu=0.01: We assume ~1% of our training data might be outliers (noise)
    # gamma='scale': Automatically optimizes for feature variance
    clf = OneClassSVM(kernel='rbf', gamma='scale', nu=0.01)
    clf.fit(X_train)
    
    print(f" -> Training Complete ({time.time() - start_time:.2f} seconds)")
    
    # Save the brain
    joblib.dump(clf, os.path.join(MODEL_PATH, "one_class_svm.pkl"))
    print(" -> Model saved to Models/one_class_svm.pkl")
    
    # --- EVALUATE ---
    print(" -> Evaluating on Unseen Test Data (50k Normal + 50k Attack)...")
    
    # We test on a balanced mix that the model has NEVER seen before
    X_test_normal = df_normal[features].sample(n=50000, random_state=101)
    X_test_attack = df_attack[features].sample(n=50000, random_state=101)
    X_test = pd.concat([X_test_normal, X_test_attack])
    
    # The Truth: 0 = Normal, 1 = Attack
    y_true = [0]*50000 + [1]*50000
    
    # The Prediction
    # SVM outputs: 1 (Normal) and -1 (Anomaly)
    y_pred_raw = clf.predict(X_test)
    
    # Convert to our format: 1->0 (Normal), -1->1 (Attack)
    y_pred = [0 if x == 1 else 1 for x in y_pred_raw]
    
    print("\n[One-Class SVM Results]")
    print(confusion_matrix(y_true, y_pred))
    print(classification_report(y_true, y_pred, target_names=['Normal', 'Attack']))

def train_random_forest(df_normal, df_attack):
    print("\n--- Training Model 2: Random Forest (Supervised Classifier) ---")
    print("(Concept: 'I have studied both Normal and Attack data. I can distinguish them.')")
    
    features = ['qber_rolling', 'basis_match', 'error']
    
    # --- TRAIN ---
    # Random Forest is fast. We use 500,000 total rows for maximum robustness.
    print(" -> Preparing Training Data (250k Normal + 250k Attack)...")
    
    df_n_sample = df_normal.sample(n=250000, random_state=42)
    df_a_sample = df_attack.sample(n=250000, random_state=42)
    
    df_combined = pd.concat([df_n_sample, df_a_sample])
    
    X = df_combined[features]
    y = df_combined['label_code']
    
    # Split: 70% for Training, 30% for immediate Validation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    
    print(" -> Training Start...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    print(" -> Training Complete")
    
    # Save the brain
    joblib.dump(rf, os.path.join(MODEL_PATH, "random_forest.pkl"))
    print(" -> Model saved to Models/random_forest.pkl")
    
    # --- EVALUATE ---
    print(" -> Evaluating...")
    y_pred = rf.predict(X_test)
    
    print("\n[Random Forest Results]")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'Attack']))

def main():
    # 1. Load Data
    df_normal, df_attack = load_data()
    
    # 2. Train the Anomaly Detector
    train_one_class_svm(df_normal, df_attack)
    
    # 3. Train the Classifier
    train_random_forest(df_normal, df_attack)
    
    print("\n--- Phase 3 Complete: AI Models are Ready ---")

if __name__ == "__main__":
    main()