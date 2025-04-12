from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5444/iot_db")

# Set up the database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declare a base class for SQLAlchemy models
Base = declarative_base()

# Define the new table model to store predictions
class SensorDataPrediction(Base):
    __tablename__ = "sensor_data_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    feed_id = Column(String, index=True)
    temperature = Column(Float)
    fan_status = Column(Integer)  # 0 or 1
    predicted_fan_status = Column(Integer)  # 0 or 1
    timestamp = Column(DateTime)

# Function to create the table
def create_prediction_table():
    Base.metadata.create_all(bind=engine)
    print("Created 'sensor_data_predictions' table successfully.")

# Fetch merged data from the database
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

# Preprocess data for training
def preprocess_data(df):
    df = df.dropna()  # Remove rows with missing values
    X = df[['temperature']]  # Feature (temperature)
    y = df['fan_status']  # Target (fan status)
    return X, y

# Train the KNN model
def train_knn_model(X_train, y_train, n_neighbors=5):
    model = KNeighborsClassifier(n_neighbors=n_neighbors)
    model.fit(X_train, y_train)
    return model

# Evaluate the model
def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    return accuracy

# Insert predictions into the new table
def insert_predictions_into_new_table(df, model):
    db = SessionLocal()
    try:
        # Loop through each row of the DataFrame and make predictions
        for index, row in df.iterrows():
            predicted_fan_status = model.predict([[row['temperature']]])[0]
            
            # Prepare data to insert
            new_prediction = SensorDataPrediction(
                id=int(row['id']),  # Ensure id is an integer
                device_id=row['device_id'],
                feed_id=row['feed_id'],
                temperature=row['temperature'],
                fan_status=int(row['fan_status']),  # Ensure fan_status is an integer
                predicted_fan_status=int(predicted_fan_status),  # Ensure predicted_fan_status is an integer
                timestamp=row['timestamp']
            )
            
            # Insert the prediction into the new table
            db.add(new_prediction)
        
        db.commit()
        print(f"Inserted {len(df)} records into 'sensor_data_predictions' table.")
    
    except Exception as e:
        db.rollback()
        print(f"Error inserting predictions: {str(e)}")
    
    finally:
        db.close()

# Main function to run the KNN model and store predictions
def run_knn_model():
    # Create the new table if it doesn't exist
    create_prediction_table()
    # df = fetch_merged_data()    
    
     
    # Generate synthetic data for now since real data is not available
    temperatures = np.random.uniform(10, 35, 1000) 
    fan_statuses = [1 if (temp > 28 or (temp > 20 and np.random.rand() > 0.5)) else 0 for temp in temperatures]  
    
    # Add a device_id column to the DataFrame
    device_ids = ["device-" + str(i % 10) for i in range(1000)]  # 10 unique device IDs for example
    
    df = pd.DataFrame({
        'id': range(1, 1001),
        'temperature': temperatures,
        'fan_status': fan_statuses,
        'device_id': device_ids,  # Ensure device_id is part of the DataFrame
        'feed_id': ['yolo-temp'] * 1000,  # Dummy feed_id (this can be adjusted as needed)
        'timestamp': pd.to_datetime('2025-04-08 00:00:00') + pd.to_timedelta(range(1000), unit='m')  # Adding timestamp
    })
    
    # Preprocess the data for training
    X, y = preprocess_data(df)
    
    # Split the data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train the KNN model
    model = train_knn_model(X_train, y_train)
    
    # Evaluate the model
    accuracy = evaluate_model(model, X_test, y_test)
    print(f"Model accuracy: {accuracy * 100:.2f}%")
    
    # Insert predictions into the new table
    insert_predictions_into_new_table(df, model)
if __name__ == "__main__":
    run_knn_model()