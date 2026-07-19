import { GoogleGenerativeAI } from "@google/generative-ai";
import { initializeApp } from "firebase/app";
import { getFirestore, collection, getDocs, doc, setDoc } from "firebase/firestore";

// SECURITY: Use environment variables, not hardcoded strings!
const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY,
  authDomain: process.env.FIREBASE_AUTH_DOMAIN,
  projectId: process.env.FIREBASE_PROJECT_ID,
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.FIREBASE_APP_ID
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// Use server-side secure env variable
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  const { sessionId } = req.body;
  if (!sessionId) return res.status(400).json({ error: 'Missing sessionId' });

  try {
    const telemetryRef = collection(db, `sessions/${sessionId}/telemetry`);
    const snapshot = await getDocs(telemetryRef);
    
    let logsList = [];
    snapshot.forEach(doc => {
        const d = doc.data();
        logsList.push(`[${d.timestamp}] State: ${d.status} | Observations: ${d.doctor_note} | Speech: ${d.transcript}`);
    });

    if (logsList.length === 0) return res.status(200).json({ success: true, soap_note: "No data to summarize." });

    const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });
    const prompt = `Review this medical telemetry: ${logsList.join('\n')}. Provide a formal SOAP note.`;
    
    const result = await model.generateContent(prompt);
    const soapNote = result.response.text();

    await setDoc(doc(db, "sessions", sessionId), {
        completed_at: new Date().toISOString(),
        soap_note: soapNote
    }, { merge: true });

    return res.status(200).json({ success: true, soap_note: soapNote });
  } catch (error) {
    return res.status(500).json({ error: "Failed to generate SOAP note" });
  }
}