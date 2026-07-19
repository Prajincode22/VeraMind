from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import csv
import os

app = FastAPI()

# ---> CHANGE THIS LABEL BEFORE EACH RECORDING <---
CURRENT_LABEL = "Frustrated"  # Options: "Normal", "Lethargic", "Pain", "Frustrated"
CSV_FILE = "facial_data.csv"

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n" + "="*40)
    print(" 🔴 RECORDING MODE ACTIVE")
    print(f" TARGET LABEL: '{CURRENT_LABEL}'")
    print("="*40 + "\n")
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("type") == "facial_telemetry":
                face_data = payload.get("data", {})
                
                # Setup CSV and headers if it doesn't exist yet
                file_exists = os.path.exists(CSV_FILE)
                with open(CSV_FILE, mode='a', newline='') as f:
                    headers = ["label"] + list(face_data.keys())
                    writer = csv.DictWriter(f, fieldnames=headers)
                    
                    if not file_exists:
                        writer.writeheader()
                    
                    # Attach the label and save the 52 points
                    face_data["label"] = CURRENT_LABEL
                    writer.writerow(face_data)
                    
                    print(f"Captured 1 frame of '{CURRENT_LABEL}'...")
                    
    except WebSocketDisconnect:
        print("\nRecording stopped. Camera disconnected.")