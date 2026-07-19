from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import pickle
import os
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google import genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
ai_client = genai.Client()

# --- Cloud Firebase Firestore Initialization ---
fb_creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if fb_creds_json:
    cred_dict = json.loads(fb_creds_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    print("Connected to Firebase Cloud Firestore successfully!")
else:
    print("WARNING: FIREBASE_CREDENTIALS_JSON variable missing. Data will not log to cloud.")

db = firestore.client() if fb_creds_json else None

# Load Custom ML Model
print("Loading Clinical ML Model...")
with open("clinical_model.pkl", "rb") as f:
    clinical_model = pickle.load(f)
print("Model Loaded Successfully!")

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

def generate_soap_note(session_id: str):
    """Fetches logs from Cloud Firestore and prompts Gemini to build the medical summary."""
    if not db:
        return

    print(f"Pulling timeline from Firestore cloud for session {session_id}...")
    docs = db.collection("sessions").document(session_id).collection("telemetry").order_by("timestamp").stream()
    
    logs_list = []
    for doc in docs:
        d = doc.to_dict()
        logs_list.append(f"[{d.get('timestamp')}] State: {d.get('status')} | Observations: {d.get('doctor_note')} | Speech: {d.get('transcript')}")

    if not logs_list:
        print("No telemetry records found in the cloud. Skipping SOAP note.")
        return

    formatted_logs = "\n".join(logs_list)

    prompt = f"""
    You are an expert clinical AI documentation assistant for an Indian hospital. 
    Review the following multi-modal sensor fusion timeline tracked during a telehealth call:
    
    {formatted_logs}

    Task:
    1. Translate any regional Indian language transcripts into English.
    2. Cross-reference what the patient explicitly said with their synchronized emotional metrics.
    3. Generate a highly accurate, professional medical SOAP Note in ENGLISH:
       - SUBJECTIVE: Patient presentation and translated summary of their spoken statements.
       - OBJECTIVE: Specific data points tracked (e.g., frequency of Pain/Distress indicators).
       - ASSESSMENT: Clinical synthesis of combined facial/vocal metrics and spoken words.
       - PLAN: Suggested follow-ups.
    """

    try:
        print(f"\nGenerating Automated SOAP Summary for Session {session_id} via Gemini...")
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        print("\n=== GENERATED SOAP NOTE ===")
        print(response.text)
        print("============================\n")
        
        db.collection("sessions").document(session_id).set({
            "completed_at": datetime.now().isoformat(),
            "soap_note": response.text
        }, merge=True)
        print("SOAP Note successfully uploaded to Firebase Cloud!")
            
    except Exception as e:
        print(f"Error communicating with Gemini API: {e}")

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_session = datetime.now().strftime("SESS-%Y%m%d-%H%M%S")
    print(f"Doctor HUD connected. Live cloud session started: {current_session}")
    
    if db:
        db.collection("sessions").document(current_session).set({
            "started_at": datetime.now().isoformat(),
            "status": "ACTIVE"
        })

    latest_standard_emotion = "Neutral"
    latest_confidence = 1.0
    latest_volume = 0.0
    latest_pitch = 0.0
    latest_transcript = "No speech detected."
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            payload_type = payload.get("type")
            
            if payload_type == "audio_telemetry":
                audio_data = payload.get("data", {})
                latest_volume = audio_data.get("volume", 0.0)
                latest_pitch = audio_data.get("pitch", 0.0)
            
            elif payload_type == "speech_transcript":
                speech_data = payload.get("data", {})
                latest_transcript = f"({speech_data.get('language')}): {speech_data.get('text')}"
                print(f"Speech Received -> {latest_transcript}")

            elif payload_type == "emotion_api":
                latest_standard_emotion = payload.get("dominant_emotion", "Neutral").capitalize()
                latest_confidence = payload.get("confidence", 0.0)
                
            elif payload_type == "facial_telemetry":
                face_data = payload.get("data", {})
                features = {shape: face_data.get(shape, 0.0) for shape in BLENDSHAPES}
                df_features = pd.DataFrame([features])
                prediction = clinical_model.predict(df_features)[0]
                
                if prediction == "Pain":
                    status = "Pain / Distress"
                    note = "ML Model detected wincing or pain expressions."
                elif prediction == "Lethargic":
                    status = "Lethargic"
                    note = "ML Model detected heavy eyelids or facial drooping."
                elif prediction == "Frustrated":
                    status = "Frustrated / Tense"
                    note = "ML Model detected jaw tension and pressed lips."
                else:
                    status = "Normal"
                    note = "Patient appears alert and comfortable."
                
                fusion_note = note
                if prediction == "Pain" and latest_volume > 40.0:
                    status = "SEVERE DISTRESS"
                    fusion_note = f"CRITICAL: {note} Accompanied by loud/strained vocalizations."
                elif prediction == "Frustrated" and latest_volume > 50.0:
                    status = "HIGHLY AGITATED"
                    fusion_note = f"ALERT: {note} Accompanied by raised voice."
                elif prediction == "Lethargic" and 0 < latest_volume < 20.0:
                    fusion_note = f"{note} Voice energy is abnormally weak."
                
                audio_diagnostics_str = f"Vol: {latest_volume:.0f} | Pitch: {latest_pitch:.0f} Hz"
                doctor_note_full = f"{fusion_note} | face-api.js: {latest_confidence*100:.1f}% UI: {latest_standard_emotion}."

                if db:
                    db.collection("sessions").document(current_session).collection("telemetry").add({
                        "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-4],
                        "status": status,
                        "audio_diagnostics": audio_diagnostics_str,
                        "transcript": latest_transcript,
                        "doctor_note": doctor_note_full
                    })

                insight = {
                    "type": "clinical_alert",
                    "data": {
                        "vocal_stress_level": f"{status} | UI: {latest_standard_emotion}", 
                        "live_transcript": f"Audio Diagnostics -> {audio_diagnostics_str}",
                        "doctor_note": doctor_note_full
                    }
                }
                await websocket.send_json(insight)
                
    except WebSocketDisconnect:
        print(f"Doctor HUD disconnected for session {current_session}.")
        if db:
            db.collection("sessions").document(current_session).update({"status": "COMPLETED"})
        generate_soap_note(current_session)