from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import json
import pickle
import pandas as pd
import cv2
import mediapipe as mp
import numpy as np
from moviepy import VideoFileClip
import os
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the ML Model
print("Loading Clinical ML Model...")
with open("clinical_model.pkl", "rb") as f:
    clinical_model = pickle.load(f)

# Initialize Native Python MediaPipe Face Landmarker
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

mp_options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='face_landmarker.task'),
    output_face_blendshapes=True,
    running_mode=VisionRunningMode.VIDEO, 
    num_faces=1
)
landmarker = FaceLandmarker.create_from_options(mp_options)

# Global tracking for the live dashboard socket connection
active_websocket = None

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

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    global active_websocket
    await websocket.accept()
    active_websocket = websocket
    print("Doctor HUD dashboard linked to the processing channel.")
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        active_websocket = None
        print("Doctor HUD disconnected.")

async def process_video_file(file_path: str):
    global active_websocket
    if not active_websocket:
        print("Aborting: No active dashboard WebSocket connection found to stream data to.")
        return

    print(f"Starting analysis on video: {file_path}")
    
    # 1. Process Audio Track using MoviePy & NumPy
    video_clip = VideoFileClip(file_path)
    audio_clip = video_clip.audio
    
    # Extract audio data array
    sr = 44100  # Sample rate
    audio_frames = list(audio_clip.iter_frames(fps=sr, dtype='float32'))
    audio_data = np.array(audio_frames)
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1) # Convert stereo to mono

    # 2. Process Video Frames using OpenCV
    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_delay = 1.0 / fps # Keep processing synced to video speed

    frame_idx = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        timestamp_ms = int((frame_idx / fps) * 1000)
        
        # Calculate Audio parameters for this specific frame time window
        start_sample = int((frame_idx / fps) * sr)
        end_sample = int(((frame_idx + 1) / fps) * sr)
        audio_window = audio_data[start_sample:end_sample]
        
        volume = 0.0
        pitch = 0.0
        if len(audio_window) > 0:
            # RMS Volume
            volume = float(np.sqrt(np.mean(audio_window**2)) * 100)
            # Basic FFT for dominant Pitch peak
            fft_data = np.abs(np.fft.rfft(audio_window))
            frequencies = np.fft.rfftfreq(len(audio_window), d=1.0/sr)
            pitch = float(frequencies[np.argmax(fft_data)]) if volume > 2.0 else 0.0

        # Convert image color spaces for MediaPipe processing
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Extract Blendshapes
        detection_result = landmarker.detect_for_video(mp_image, timestamp_ms)
        
        prediction = "Normal" # Default
        if detection_result.face_blendshapes and len(detection_result.face_blendshapes) > 0:
            blendshape_categories = detection_result.face_blendshapes[0]
            # Match the input structure required by the trained .pkl file
            features = {}
            for category in blendshape_categories:
                name = category.category_name
                if name in BLENDSHAPES:
                    features[name] = category.score if category.score > 0.1 else 0.0
            
            # Pad missing shapes
            for b in BLENDSHAPES:
                if b not in features:
                    features[b] = 0.0
                    
            df_features = pd.DataFrame([features])[BLENDSHAPES]
            prediction = clinical_model.predict(df_features)[0]

        # Multi-Modal Sensor Fusion Engine Integration
        status = "Normal"
        note = "Patient appears stable."
        
        if prediction == "Pain":
            status = "Pain / Distress"
            note = "ML Model detected wincing or pain expressions."
            if volume > 30.0:
                status = "SEVERE DISTRESS"
                note = "CRITICAL: Facial pain combined with high vocal stress."
        elif prediction == "Lethargic":
            status = "Lethargic"
            note = "ML Model detected heavy eyelids or facial drooping."
        elif prediction == "Frustrated":
            status = "Frustrated / Tense"
            note = "ML Model detected jaw tension and pressed lips."

        # Emit the fused telemetric frame straight to the UI
        insight = {
            "type": "clinical_alert",
            "data": {
                "vocal_stress_level": f"{status} (Offline File Sim)", 
                "live_transcript": f"Timeline: {timestamp_ms/1000:.1f}s | Vol: {volume:.1f} | Pitch: {pitch:.0f} Hz",
                "doctor_note": f"{note} (Standard Emotion: Processing)"
            }
        }
        
        try:
            await active_websocket.send_json(insight)
        except Exception:
            break # Socket closed, drop out

        frame_idx += 1
        await asyncio.sleep(frame_delay) # Yield to maintain realistic playback pace

    cap.release()
    video_clip.close()
    os.remove(file_path) # Clean up temp space
    print("Video batch analysis complete.")

@app.post("/api/upload-video")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Execute the heavy processing pipeline safely in the background
    background_tasks.add_task(process_video_file, temp_path)
    return {"status": "Processing initiated", "filename": file.filename}