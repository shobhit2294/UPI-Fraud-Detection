import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
import os

# Load dataset
df = pd.read_csv("dataset/Bank_Transaction_Fraud_Detection.csv")

# Encode categorical columns
le_device = LabelEncoder()
le_location = LabelEncoder()

df["device_type"] = le_device.fit_transform(df["device_type"])
df["location"] = le_location.fit_transform(df["location"])

# Features & target
X = df.drop("is_fraud", axis=1)
y = df["is_fraud"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save model
joblib.dump(model, "fraud_model.pkl")

print("✅ Model trained successfully and saved.")
