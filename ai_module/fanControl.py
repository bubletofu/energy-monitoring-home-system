# ai_module/fanControl.py
#psql -h localhost -p 5433 -U postgres -d iot_db
# yolo_fan, yolo_temp, yolo_light
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5433/iot_db")
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set up the database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Start a session to interact with the database
db = SessionLocal()

from sqlalchemy import text

try:
    db.execute(text("ALTER TABLE sensor_data ADD COLUMN IF NOT EXISTS predicted_fan_status INTEGER"))
    db.commit()
    print("Column 'predicted_fan_status' added successfully.")
except Exception as e:
    db.rollback()
    print(f"Error adding column: {str(e)}")


def fetch_merged_data():
    query = """
        SELECT 
            f.timestamp,
            f.value AS fan_status,
            t.value AS temperature
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
    
    # Print the shape to debug
    print(f"Fetched merged data shape: {df.shape}")
    
    return df
def preprocess_data(df):
    """
    Preprocess the merged data for training.
    """
    df = df.dropna()
    X = df[['temperature']] 
    y = df['fan_status']  
    return X, y

from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def train_knn_model(X_train, y_train, n_neighbors=5):
    """
    Train a KNN model to predict fan status based on temperature.
    """
    model = KNeighborsClassifier(n_neighbors=n_neighbors)
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    """
    Evaluate the KNN model and return the accuracy.
    """
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    return accuracy

def update_database_with_predictions(df, model):
    """
    Update the database with the predicted fan status (0 or 1).
    """
    with engine.connect() as connection:
        for index, row in df.iterrows():
            predicted_fan_status = model.predict([[row['temperature']]])

            predicted_fan_status = int(predicted_fan_status[0]) 
            record_id = int(row['id']) 

            query = text("""
                UPDATE sensor_data
                SET predicted_fan_status = :predicted_fan_status
                WHERE id = :id
            """)
            connection.execute(query, {'predicted_fan_status': predicted_fan_status, 'id': record_id})

    print("Database updated with predicted fan status.")
    
def run_knn_model():
    """
    Main function to run the KNN model for training, prediction, and database update.
    """
    df = fetch_merged_data()
    print('shape: ',df.shape[0])

    X, y = preprocess_data(df)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = train_knn_model(X_train, y_train)

    accuracy = evaluate_model(model, X_test, y_test)
    print(f"Model accuracy: {accuracy * 100:.2f}%")

    update_database_with_predictions(df, model)

    return model