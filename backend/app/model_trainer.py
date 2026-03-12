import pandas as pd
import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from data_loader import load_dataset, generate_training_pairs
from matching_service import calculate_match

def train_mlr_model():
    """
    Train Multiple Linear Regression model on generated pairs.
    Save model.pkl and scaler.pkl.
    """
    print("Loading dataset...")
    load_dataset()
    
    print("Generating training pairs...")
    pairs_df = generate_training_pairs()
    
    if pairs_df.empty:
        print("No training pairs generated!")
        return
    
    print(f"Generated {len(pairs_df)} pairs")
    
    X = np.array(pairs_df['features'].tolist())
    y = pairs_df['heuristic_score']
    
    print(f"Features shape: {X.shape}")
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train model
    model = LinearRegression()
    model.fit(X_scaled, y)
    
    # Evaluate
    train_score = model.score(X_scaled, y)
    print(f"R^2 score on train: {train_score:.4f}")
    
    # Save
    joblib.dump(model, 'model.pkl')
    joblib.dump(scaler, 'scaler.pkl')
    
    print("Model and scaler saved as model.pkl and scaler.pkl")
    print("To use: import joblib; model=joblib.load('model.pkl'); scaler=joblib.load('scaler.pkl')")

if __name__ == "__main__":
    train_mlr_model()

