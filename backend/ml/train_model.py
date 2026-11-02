import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib

# ---------------- LOAD DATA ----------------
df = pd.read_csv("Bank_Transaction_Fraud_Detection.csv")

# ---------------- KEEP ONLY REQUIRED COLUMNS ----------------
use_cols = [
    "Transaction_Amount",
    "Account_Balance",
    "City",
    "Device_Type",
    "Transaction_Type",
    "Age",
    "Is_Fraud"
]

df = df[use_cols]

# ---------------- HANDLE CATEGORICAL ----------------
encoders = {}

for col in ["City", "Device_Type", "Transaction_Type"]:
    le = LabelEncoder()
    df[col] = df[col].astype(str)
    le.fit(df[col])
    df[col] = le.transform(df[col])
    encoders[col] = le

# ---------------- SPLIT ----------------
X = df.drop("Is_Fraud", axis=1)
y = df["Is_Fraud"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ---------------- TRAIN ----------------
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    class_weight="balanced",
    random_state=42
)

model.fit(X_train, y_train)

# ---------------- SAVE ----------------
joblib.dump(model, "fraud_model.pkl")
joblib.dump(encoders, "encoders.pkl")

print(" Simplified fraud ML model trained successfully")
