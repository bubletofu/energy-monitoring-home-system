#ai_module/fanControl.py

import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from dotenv import load_dotenv

from visualize import (
    generate_visualizations,     
    plot_classification_report,  
    plot_confusion_matrix,
    plot_roc_auc,
)
# Load environment variables
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5444/iot_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SensorDataPrediction(Base):
    __tablename__ = "sensor_data_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    feed_id = Column(String, index=True)
    temperature = Column(Float)
    fan_status = Column(Integer)  # 0 or 1
    predicted_fan_status = Column(Integer)  # 0 or 1
    timestamp = Column(DateTime)

def generate_synthetic_data(n_samples=1000):
    np.random.seed(42)
    temperatures = np.random.uniform(10, 35, n_samples)
    fan_statuses = [1 if (temp > 28 or (temp > 20 and np.random.rand() > 0.5)) else 0 for temp in temperatures]
    
    df = pd.DataFrame({
        'id': range(1, n_samples + 1),
        'temperature': temperatures,
        'fan_status': fan_statuses,
        'device_id': ["device-" + str(i % 10) for i in range(n_samples)],
        'feed_id': ['yolo-fan'] * n_samples,
        'timestamp': pd.to_datetime('2025-04-08 00:00:00') + pd.to_timedelta(range(n_samples), unit='m')
    })
    print(f"Generated synthetic data shape: {df.shape}")
    return df

def fetch_merged_data():
    query = """
        SELECT 
            f.timestamp,
            f.value AS fan_status,
            t.value AS temperature,
            f.id,
            f.device_id,
            f.feed_id
        FROM
            sensor_data f
        JOIN
            sensor_data t
        ON 
            f.timestamp = t.timestamp
        WHERE
            f.feed_id = 'yolo-fan'
        AND 
            t.feed_id = 'yolo-temp';
    """
    df = pd.read_sql(query, engine)
    print(f"Fetched merged data shape: {df.shape}")
    return df

def preprocess_data(df):
    df = df.dropna()  # Remove rows with missing values
    X = df[['temperature']]  # Feature (temperature)
    y = df['fan_status']  # Target (fan status)
    return X, y

def train_knn_model(X_train, y_train, n_neighbors=5):
    model = KNeighborsClassifier(n_neighbors=n_neighbors)
    model.fit(X_train, y_train)
    return model

def train_rf_model(X_train, y_train, n_estimators=100):
    model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
    model.fit(X_train, y_train)
    return model

def train_lr_model(X_train, y_train):
    model = LogisticRegression(random_state=42)
    model.fit(X_train, y_train)
    return model

def compare_models(X_train, X_test, y_train, y_test, output_dir="ai_module/fan_plots"):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Train models
    knn_model = train_knn_model(X_train, y_train)
    rf_model = train_rf_model(X_train, y_train)
    lr_model = train_lr_model(X_train, y_train)
    
    # Get predictions
    knn_pred = knn_model.predict(X_test)
    rf_pred = rf_model.predict(X_test)
    lr_pred = lr_model.predict(X_test)
    
    # Get decision scores for ROC-AUC (if binary classification)
    knn_scores = knn_model.predict_proba(X_test)[:, 1] if hasattr(knn_model, "predict_proba") else None
    rf_scores = rf_model.predict_proba(X_test)[:, 1]
    lr_scores = lr_model.predict_proba(X_test)[:, 1]
    
    print("\n=== Fan Status Model Comparison ===")
    print("\nKNN (fan_status):")
    print(classification_report(y_test, knn_pred))
    print("\nRandom Forest (fan_status):")
    print(classification_report(y_test, rf_pred))
    print("\nLogistic Regression (fan_status):")
    print(classification_report(y_test, lr_pred))
    
    # Generate visualizations for each model
    models = {
        "knn": (knn_model, knn_pred, knn_scores),
        "rf": (rf_model, rf_pred, rf_scores),
        "lr": (lr_model, lr_pred, lr_scores)
    }
    
    for model_name, (model, y_pred, y_scores) in models.items():
        # Plot classification report
        classification_report_path = os.path.join(output_dir, f'{model_name}_classification_report.png')
        plot_classification_report(y_test, y_pred, classification_report_path)
        
        # Plot confusion matrix
        confusion_matrix_path = os.path.join(output_dir, f'{model_name}_confusion_matrix.png')
        plot_confusion_matrix(y_test, y_pred, confusion_matrix_path)
        
        # Plot ROC-AUC curve (if binary classification and scores are available)
        if len(np.unique(y_test)) == 2 and y_scores is not None:
            roc_auc_path = os.path.join(output_dir, f'{model_name}_roc_auc_curve.png')
            plot_roc_auc(y_test, y_scores, roc_auc_path)
    
    print(f"Visualizations saved in {output_dir}")
    
    # Return Random Forest model for potential further use
    return rf_model

def run_knn_model():
    df = fetch_merged_data()
    
    X, y = preprocess_data(df)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Comparing models...")
    model = compare_models(X_train, X_test, y_train, y_test)

    

if __name__ == "__main__":
    run_knn_model()