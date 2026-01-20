def predict_fraud(amount: float):
    if amount > 7000:
        return "fraud", 92.5
    elif amount > 3000:
        return "suspicious", 65.0
    else:
        return "safe", 10.0
