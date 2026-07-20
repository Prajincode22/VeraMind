#  VeraMind: AI-Powered Psychiatric Telemedicine Platform

VeraMind is an advanced, real-time telemedicine application designed to augment clinical workflows. By leveraging a custom **Tri-Modal AI Pipeline**, the platform analyzes facial landmarks, emotional states, and multilingual vocal stress during a live patient consultation. Upon concluding the call, VeraMind automatically synthesizes the session's telemetry data into a professional clinical SOAP note using Google's Gemini 3.5 Flash model.

## Key Features

* **Real-Time Telehealth Video:** Low-latency peer-to-peer video streaming infrastructure.
* ** Tri-Modal AI Telemetry Pipeline:**
  * **Facial Landmarking:** Tracks micro-expressions and physical distress markers using MediaPipe.
  * **Emotion Recognition:** Analyzes cognitive state (e.g., normal, frustrated, lethargic) using `face-api.js` and a custom compiled clinical model.
  * **Multilingual Transcription:** Captures real-time patient speech across 8+ local and regional languages via the Web Speech API.
* ** Live Doctor HUD:** Displays instantaneous vocal stress levels, live transcripts, and automated clinical insights overlaid on the video feed.
* ** Automated SOAP Notes:** Generates highly accurate, structured clinical summaries post-call via a Vercel Serverless backend integrated with Google Gemini 3.5 Flash.
* ** Cloud Synchronization:** Logs all session telemetry securely to Firebase Firestore for compliance and historical review.

---

## Technology Stack

**Frontend Architecture**
* [React](https://reactjs.org/) & [Vite](https://vitejs.dev/)
* [Agora RTC SDK](https://www.agora.io/en/) (Video/Audio Streaming)
* [MediaPipe Tasks Vision](https://developers.google.com/mediapipe) (Facial Landmarking)
* [face-api.js](https://justadudewhohacks.github.io/face-api.js/docs/index.html) (Emotion Detection)
* Web Speech API (Live Transcription)

**Backend & Cloud Infrastructure**
* [Vercel Serverless Functions](https://vercel.com/docs/functions) (API Routes)
* [Firebase Firestore](https://firebase.google.com/docs/firestore) (NoSQL Database)
* [Google Gemini API (3.5 Flash)](https://ai.google.dev/) (LLM Summarization)

---

##  Local Development Setup

### 1. Prerequisites
Ensure you have the following installed on your local machine:
* [Node.js](https://nodejs.org/) (v18 or higher recommended)
* Git

### 2. Clone the Repository
```bash
git clone [https://github.com/your-username/VeraMind.git](https://github.com/your-username/VeraMind.git)
cd VeraMind