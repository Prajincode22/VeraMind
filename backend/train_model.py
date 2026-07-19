import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle

# 1. Load the synthetic dataset
print("Loading facial_data.csv...")
df = pd.read_csv("facial_data.csv")

# 2. Separate features (the 52 blendshapes) and target labels
X = df.drop("label", axis=1)
y = df["label"]

# 3. Split into training and testing sets (80% for training, 20% for testing)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Train the Random Forest AI
print("Training the Clinical AI model...")
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# 5. Test its accuracy
y_pred = clf.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Model Training Complete! Accuracy: {accuracy * 100:.2f}%")

# 6. Save the trained brain to a file
with open("clinical_model.pkl", "wb") as f:
    pickle.dump(clf, f)
    
print("Saved AI model as 'clinical_model.pkl'. Ready for live integration!")