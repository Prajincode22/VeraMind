import csv
import random

# The 52 facial blendshapes exported by MediaPipe WebAssembly
BLENDSHAPES = [
    "_neutral", "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft",
    "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight", "eyeLookUpLeft",
    "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight", "jawForward",
    "jawLeft", "jawOpen", "jawRight", "mouthClose", "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft",
    "mouthFrownRight", "mouthFunnel", "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft",
    "mouthPressRight", "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower",
    "mouthShrugUpper", "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight"
]

def generate_row(label):
    # Start with standard background noise (0.0 to 0.1) for all 52 muscles
    row = {shape: round(random.uniform(0.0, 0.1), 3) for shape in BLENDSHAPES}
    row["label"] = label
    
    if label == "Normal":
        # Just random blinks and slight movements
        row["eyeBlinkLeft"] = round(random.uniform(0.0, 0.2), 3)
        row["eyeBlinkRight"] = row["eyeBlinkLeft"] + random.uniform(-0.05, 0.05)
        
    elif label == "Lethargic":
        # Heavy, drooping eyes and slight frowning
        row["eyeBlinkLeft"] = round(random.uniform(0.4, 0.8), 3)
        row["eyeBlinkRight"] = row["eyeBlinkLeft"] + random.uniform(-0.1, 0.1)
        row["mouthFrownLeft"] = round(random.uniform(0.2, 0.5), 3)
        row["mouthFrownRight"] = row["mouthFrownLeft"] + random.uniform(-0.05, 0.05)
        row["jawOpen"] = round(random.uniform(0.1, 0.3), 3) # Slack jaw
        
    elif label == "Pain":
        # Squinting, heavy brow furrow, and nose sneering
        row["browDownLeft"] = round(random.uniform(0.5, 0.9), 3)
        row["browDownRight"] = row["browDownLeft"] + random.uniform(-0.1, 0.1)
        row["noseSneerLeft"] = round(random.uniform(0.4, 0.8), 3)
        row["noseSneerRight"] = row["noseSneerLeft"] + random.uniform(-0.1, 0.1)
        row["eyeSquintLeft"] = round(random.uniform(0.3, 0.7), 3)
        row["eyeSquintRight"] = row["eyeSquintLeft"] + random.uniform(-0.1, 0.1)
        row["mouthPressLeft"] = round(random.uniform(0.3, 0.6), 3) # Tight lips
        row["mouthPressRight"] = row["mouthPressLeft"] + random.uniform(-0.05, 0.05)
        
    # Ensure no values exceed 1.0 or drop below 0.0
    for key in row:
        if key != "label":
            row[key] = max(0.0, min(1.0, row[key]))
            
    return row

print("Generating synthetic clinical dataset...")

# Generate 1000 frames for each state
dataset = []
for _ in range(1000):
    dataset.append(generate_row("Normal"))
    dataset.append(generate_row("Lethargic"))
    dataset.append(generate_row("Pain"))

# Write to CSV
with open("facial_data.csv", mode="w", newline="") as f:
    headers = ["label"] + BLENDSHAPES
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(dataset)

print(f"Success! Created 'facial_data.csv' with {len(dataset)} rows of mathematical facial telemetry.")