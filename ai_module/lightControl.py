from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from dotenv import load_dotenv

from visualize import (
    plot_classification_report,
    plot_confusion_matrix,
    plot_roc_auc,
)

# Load environment variables
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5444/iot_db")

# Set up the database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declare a base class for SQLAlchemy models
Base = declarative_base()

# Define the new table model to store light predictions
class LightDataPrediction(Base):
    __tablename__ = "light_data_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    feed_id = Column(String, index=True)
    temperature = Column(Float)
    led_mode = Column(Integer)  # 0 (manual/AI) or 1 (threshold-based)
    led_num = Column(Integer)  # 0, 1, 2, 3, or 4 (number of LEDs on)
    predicted_led_mode = Column(Integer)  # 0 or 1
    predicted_led_num = Column(Integer)  # 0, 1, 2, 3, or 4
    timestamp = Column(DateTime)

# Function to create the table
def create_prediction_table():
    Base.metadata.create_all(bind=engine)
    print("Created 'light_data_predictions' table successfully.")

def generate_synthetic_data():
    np.random.seed(42)
    n_samples = 1000
    temperatures = np.random.uniform(10, 35, n_samples)
    # LED mode: 1 (threshold-based) if temp > 25, else 0 (manual/AI) with some randomness
    led_modes = [1 if temp > 25 else (0 if np.random.rand() > 0.3 else 1) for temp in temperatures]
    # LED num: 0–4 based on temperature ranges with some randomness
    led_nums = [min(4, max(0, int((temp - 10) / 5) + np.random.choice([-1, 0, 1]))) for temp in temperatures]
    
    df = pd.DataFrame({
        'id': range(1, n_samples + 1),
        'temperature': temperatures,
        'led_mode': led_modes,
        'led_num': led_nums,
        'device_id': ["device-" + str(i % 10) for i in range(n_samples)],
        'feed_id': ['yolo-light'] * n_samples,
        'timestamp': pd.to_datetime('2025-04-08 00:00:00') + pd.to_timedelta(range(n_samples), unit='m')
    })
    print(f"Generated synthetic data shape: {df.shape}")
    return df

def fetch_merged_data():
    query = """
        SELECT 
            f.timestamp,
            f.value AS light_status,
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
            f.feed_id = 'yolo-light'
        AND 
            t.feed_id = 'yolo-temp';
    """
    df = pd.read_sql(query, engine)
    print(f"Fetched merged data shape: {df.shape}")
    return df

def preprocess_data(df):
    df = df.dropna() 
    X = df[['temperature']] 
    y_mode = df['led_mode'] 
    y_num = df['led_num']   
    return X, y_mode, y_num

def generate_synthetic_data(n_samples=1000):
    np.random.seed(42)
    temperatures = np.random.uniform(10, 35, n_samples)
    # LED mode: 1 (threshold-based) if temp > 25, else 0 (manual/AI) with some randomness
    led_modes = [1 if temp > 25 else (0 if np.random.rand() > 0.3 else 1) for temp in temperatures]
    # LED num: 0–4 based on temperature ranges with some randomness
    led_nums = [min(4, max(0, int((temp - 10) / 5) + np.random.choice([-1, 0, 1]))) for temp in temperatures]
    
    df = pd.DataFrame({
        'id': range(1, n_samples + 1),
        'temperature': temperatures,
        'led_mode': led_modes,
        'led_num': led_nums,
        'device_id': ["device-" + str(i % 10) for i in range(n_samples)],
        'feed_id': ['yolo-light'] * n_samples,
        'timestamp': pd.to_datetime('2025-04-08 00:00:00') + pd.to_timedelta(range(n_samples), unit='m')
    })
    print(f"Generated synthetic data shape: {df.shape}")
    return df

# Preprocess data for training
def preprocess_data(df):
    df = df.dropna()  # Remove rows with missing values
    X = df[['temperature']]  # Feature (temperature)
    y_mode = df['led_mode']  # Target (led_mode, binary)
    y_num = df['led_num']   # Target (led_num, multiclass)
    return X, y_mode, y_num

# Train KNN models for led_mode and led_num
def train_knn_models(X_train, y_mode_train, y_num_train, n_neighbors=5):
    model_mode = KNeighborsClassifier(n_neighbors=n_neighbors)
    model_mode.fit(X_train, y_mode_train)
    model_num = KNeighborsClassifier(n_neighbors=n_neighbors)
    model_num.fit(X_train, y_num_train)
    return model_mode, model_num

# Train Random Forest models for led_mode and led_num
def train_rf_models(X_train, y_mode_train, y_num_train, n_estimators=100):
    model_mode = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
    model_mode.fit(X_train, y_mode_train)
    model_num = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
    model_num.fit(X_train, y_num_train)
    return model_mode, model_num

# Train Logistic Regression model for led_mode
def train_lr_model(X_train, y_mode_train):
    model_mode = LogisticRegression(random_state=42)
    model_mode.fit(X_train, y_mode_train)
    return model_mode

def compare_models(
    X_train, X_test,
    y_mode_train, y_mode_test,
    y_num_train,  y_num_test,
    output_dir="ai_module/light_plots"
):
    os.makedirs(output_dir, exist_ok=True)

    # ─────────── train the six estimators ───────────
    knn_mode, knn_num = train_knn_models(X_train, y_mode_train, y_num_train)
    rf_mode,  rf_num  = train_rf_models (X_train, y_mode_train, y_num_train)
    lr_mode           = train_lr_model  (X_train, y_mode_train)

    # Map nick-names → (model, y_true, y_pred, y_scores or None)
    experiments = {
        "knn_mode": (knn_mode, y_mode_test, knn_mode.predict(X_test),
                     knn_mode.predict_proba(X_test)[:, 1]),
        "rf_mode":  (rf_mode,  y_mode_test, rf_mode.predict(X_test),
                     rf_mode.predict_proba(X_test)[:, 1]),
        "lr_mode":  (lr_mode,  y_mode_test, lr_mode.predict(X_test),
                     lr_mode.predict_proba(X_test)[:, 1]),
        "knn_num":  (knn_num,  y_num_test, knn_num.predict(X_test), None),
        "rf_num":   (rf_num,   y_num_test, rf_num.predict(X_test),  None),
    }

    for tag, (model, y_true, y_pred, y_scores) in experiments.items():
        print(f"\n=== {tag.upper()} ===")
        print(classification_report(y_true, y_pred))

        plot_classification_report(
            y_true, y_pred,
            os.path.join(output_dir, f"{tag}_classification_report.png")
        )

        plot_confusion_matrix(
            y_true, y_pred,
            os.path.join(output_dir, f"{tag}_confusion_matrix.png")
        )

        if y_scores is not None and len(np.unique(y_true)) == 2:
            plot_roc_auc(
                y_true, y_scores,
                os.path.join(output_dir, f"{tag}_roc_auc_curve.png")
            )

    print(f"\n✅  All visualizations saved in “{output_dir}”.\n")

    return rf_mode, rf_num

def run_light_prediction():
    df = fetch_merged_data()
    
    X, y_mode, y_num = preprocess_data(df)
    
    X_train, X_test, y_mode_train, y_mode_test, y_num_train, y_num_test = train_test_split(
        X, y_mode, y_num, test_size=0.2, random_state=42
    )
    
    print("Comparing models...")
    model_mode, model_num = compare_models(X_train, X_test, y_mode_train, y_mode_test, y_num_train, y_num_test)
    


if __name__ == "__main__":
    run_light_prediction()