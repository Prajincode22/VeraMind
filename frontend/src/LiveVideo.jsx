import React, { useEffect, useRef, useState } from 'react';
import AgoraRTC from 'agora-rtc-sdk-ng';
import { FilesetResolver, FaceLandmarker } from '@mediapipe/tasks-vision';
import * as faceapi from 'face-api.js';
import { db } from './firebase';
import { collection, addDoc } from "firebase/firestore";
import { score } from './clinical_model';

const blendshapeNames = [
    "_neutral", "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft",
    "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight", "eyeLookUpLeft",
    "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight", "jawForward",
    "jawLeft", "jawOpen", "jawRight", "mouthClose", "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft",
    "mouthFrownRight", "mouthFunnel", "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft",
    "mouthPressRight", "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower",
    "mouthShrugUpper", "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight"
];

export default function LiveVideo({ setUiTelemetry, setSoapNote}) {
  const videoRef = useRef(null);
  const [isTracking, setIsTracking] = useState(false);
  const emotionInterval = useRef(null);
  const audioInterval = useRef(null);
  const [patientLang, setPatientLang] = useState('hi-IN'); 

  
  const latestVolume = useRef(0.0);
  const latestPitch = useRef(0.0);
  const latestTranscript = useRef("");
  const lastFirebaseLogTime = useRef(Date.now());
  
 
  const trackingActiveRef = useRef(false);
  const recognitionRef = useRef(null);

  useEffect(() => {
    let localTracks = [];
    let faceLandmarker;
    let animationFrameId;
    let audioContext;

    const initializeAIAndCamera = async () => {
      try {
        await faceapi.nets.tinyFaceDetector.loadFromUri('/models');
        await faceapi.nets.faceExpressionNet.loadFromUri('/models');

        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
        );
        
        faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
            delegate: "GPU"
          },
          outputFaceBlendshapes: true,
          runningMode: "VIDEO",
          numFaces: 1
        });

        localTracks = await AgoraRTC.createMicrophoneAndCameraTracks();
        const audioTrack = localTracks[0];
        const videoTrack = localTracks[1];
        videoTrack.play(videoRef.current);

        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 1024; 
        
        const mediaStream = new MediaStream([audioTrack.getMediaStreamTrack()]);
        const source = audioContext.createMediaStreamSource(mediaStream);
        source.connect(analyser);
        
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const bufferLength = analyser.frequencyBinCount;

        setTimeout(() => {
            const actualVideoElement = videoRef.current.querySelector('video');
            if (actualVideoElement) {
                setIsTracking(true);
                trackingActiveRef.current = true;
                predictWebcam(actualVideoElement);
                startEmotionAPI(actualVideoElement);
                startAudioTelemetry(analyser, dataArray, bufferLength, audioContext.sampleRate);
                startSpeechRecognition(); 
            }
        }, 500);

      } catch (error) {
        console.error("Error initializing AI pipeline:", error);
      }
    };

    const startAudioTelemetry = (analyser, dataArray, bufferLength, sampleRate) => {
        audioInterval.current = setInterval(() => {
            analyser.getByteFrequencyData(dataArray);
            
            let sum = 0;
            let maxEnergy = 0;
            let peakIndex = 0;
            
            for (let i = 0; i < bufferLength; i++) {
                const val = dataArray[i];
                sum += val * val;
                
                if (val > maxEnergy) {
                    maxEnergy = val;
                    peakIndex = i;
                }
            }
            
            const rmsVolume = Math.sqrt(sum / bufferLength);
            const hzPerBin = sampleRate / 2 / bufferLength;
            const peakFrequency = peakIndex * hzPerBin;

            latestVolume.current = rmsVolume;
            latestPitch.current = peakFrequency;
        }, 500);
    };

    const startSpeechRecognition = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = patientLang;

        recognition.onresult = (event) => {
            const currentTranscript = event.results[event.results.length - 1][0].transcript;
            if (currentTranscript.trim() !== '') {
                latestTranscript.current = `(${patientLang}): ${currentTranscript}`;
            }
        };

        recognition.onend = () => {
           
            if (trackingActiveRef.current && recognitionRef.current) {
                try { recognitionRef.current.start(); } catch (e) {}
            }
        };

        recognitionRef.current = recognition;
        recognition.start();
    };

    const predictWebcam = (videoElement) => {
      
      if (!trackingActiveRef.current) return;

      if (faceLandmarker) {
        const startTimeMs = performance.now();
        const results = faceLandmarker.detectForVideo(videoElement, startTimeMs);
        
        if (results.faceBlendshapes && results.faceBlendshapes.length > 0) {
            const blendshapes = results.faceBlendshapes[0].categories;
            const now = Date.now();

            const facialData = {};
            blendshapes.forEach(b => {
                facialData[b.categoryName] = b.score > 0.1 ? b.score : 0;
            });

            if (now - lastFirebaseLogTime.current > 1500) {
                const currentSession = "SESS-LIVE-001"; 
                const inputArray = blendshapeNames.map(name => facialData[name] || 0.0);
                
                let prediction;
                try {
                    prediction = score(inputArray);
                } catch(e) {
                    prediction = "Normal";
                }

                let status = "Normal";
                let note = "Patient appears alert and comfortable.";

                if (prediction === "Pain" || prediction > 0.8) { 
                    status = "Pain / Distress";
                    note = "ML Model detected wincing or pain expressions.";
                } else if (prediction === "Frustrated") {
                    status = "Frustrated / Tense";
                    note = "ML Model detected jaw tension and pressed lips.";
                } else if (prediction === "Lethargic") {
                    status = "Lethargic";
                    note = "ML Model detected heavy eyelids.";
                }

                if (status === "Pain / Distress" && latestVolume.current > 40.0) {
                    status = "SEVERE DISTRESS";
                    note = `CRITICAL: ${note} Accompanied by loud/strained vocalizations.`;
                }

                // Sending UI Telemetry 
                if (setUiTelemetry) {
                    setUiTelemetry({
                        vocal_stress_level: status,
                        live_transcript: latestTranscript.current || "Listening...",
                        doctor_note: note
                    });
                }

                const telemetryRef = collection(db, `sessions/${currentSession}/telemetry`);
                addDoc(telemetryRef, {
                    timestamp: new Date().toISOString(),
                    status: status,
                    audio_diagnostics: `Vol: ${latestVolume.current.toFixed(0)} | Pitch: ${latestPitch.current.toFixed(0)} Hz`,
                    transcript: latestTranscript.current || "No speech detected.", 
                    doctor_note: note
                }).then(() => console.log("Telemetry logged to Firebase!")).catch(e => console.error(e));

                lastFirebaseLogTime.current = now;
                latestTranscript.current = ""; 
            }
        }
        animationFrameId = requestAnimationFrame(() => predictWebcam(videoElement));
      }
    };

    const startEmotionAPI = (videoElement) => {
        emotionInterval.current = setInterval(async () => {
            if (!trackingActiveRef.current) return;
            await faceapi.detectSingleFace(
                videoElement, 
                new faceapi.TinyFaceDetectorOptions()
            ).withFaceExpressions();
        }, 1000);
    };

    initializeAIAndCamera();

    return () => {
      trackingActiveRef.current = false;
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      if (emotionInterval.current) clearInterval(emotionInterval.current);
      if (audioInterval.current) clearInterval(audioInterval.current);
      if (audioContext) audioContext.close();
      if (recognitionRef.current) {
          recognitionRef.current.onend = null; 
          recognitionRef.current.stop();
          recognitionRef.current = null;
      }
      localTracks.forEach(track => {
        track.stop();
        track.close();
      });
    };
  }, [patientLang]); 

  const [isGenerating, setIsGenerating] = useState(false);

const endCall = async () => {
    setIsGenerating(true);
    trackingActiveRef.current = false; 
    console.log("Ending call. Triggering backend SOAP generation...");
    
    try {
      
      const response = await fetch('/api/generate-soap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: "SESS-LIVE-001" }) 
      });

      const data = await response.json();
      
      if (data.success) {
        console.log("SOAP Note Received:", data.soap_note);
        setSoapNote(data.soap_note); // Updates the UI Dashboard directly
      } else {
        throw new Error(data.error || "Failed to generate summary");
      }
    } catch (error) {
      console.error("Network or API Error:", error);
      alert("Call ended, but failed to generate the summary.");
    } finally {
      setIsGenerating(false);
      setIsTracking(false); 
    }
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={videoRef} style={{ width: '100%', height: '100%', backgroundColor: '#000', borderRadius: '6px', overflow: 'hidden' }} />
      
      <div style={{ position: 'absolute', bottom: 10, left: 10, zIndex: 10 }}>
        <select 
          value={patientLang} 
          onChange={(e) => setPatientLang(e.target.value)}
          style={{ padding: '4px 8px', backgroundColor: '#1f2937', color: '#fff', border: '1px solid #374151', borderRadius: '4px', fontSize: '12px', outline: 'none', cursor: 'pointer' }}
        >
          <option value="hi-IN">Hindi (हिंदी)</option>
          <option value="ta-IN">Tamil (தமிழ்)</option>
          <option value="te-IN">Telugu (తెలుగు)</option>
          <option value="kn-IN">Kannada (ಕನ್ನಡ)</option>
          <option value="ml-IN">Malayalam (മലയാളം)</option>
          <option value="mr-IN">Marathi (मराठी)</option>
          <option value="bn-IN">Bengali (বাংলা)</option>
          <option value="en-IN">Indian English</option>
        </select>
      </div>

      <div style={{ position: 'absolute', bottom: 10, right: 10, zIndex: 10 }}>
        <button 
          onClick={endCall}
          disabled={isGenerating}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: isGenerating ? '#9ca3af' : '#ef4444', 
            color: '#fff', 
            border: 'none', 
            borderRadius: '4px', 
            fontWeight: 'bold', 
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            boxShadow: isGenerating ? 'none' : '0 0 10px rgba(239, 68, 68, 0.5)'
          }}
        >
          {isGenerating ? "Generating SOAP Note..." : "End Call"}
        </button>
      </div>

      {isTracking && (
        <div style={{ position: 'absolute', top: 10, left: 10, background: 'rgba(0,0,0,0.7)', padding: '6px 10px', borderRadius: '4px', color: '#10b981', fontSize: '12px', fontWeight: 'bold', border: '1px solid #10b981' }}>
          👁️ Tri-Modal AI Active (Face + Emotion + Multilingual Voice)
        </div>
      )}
    </div>
  );
}
