import React, { useState } from 'react';
import LiveVideo from './LiveVideo';

function App() {
  const [uiTelemetry, setUiTelemetry] = useState({
    vocal_stress_level: 'Idle',
    live_transcript: 'Awaiting patient audio feed...',
    doctor_note: 'System standby.'
  });

  // NEW: State to hold the final SOAP note from the server
  const [soapNote, setSoapNote] = useState(null);

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1>Telehealth AI Platform — Doctor HUD</h1>
        <p style={styles.status}>🟢 Online - Local Tri-Modal AI Active</p>
      </header>

      <main style={styles.grid}>
        <section style={styles.card}>
          <h2>Live Patient Feed</h2>
          <div style={styles.videoPlaceholder}>
            {/* Pass setSoapNote so the Video component can update the dashboard */}
            <LiveVideo setUiTelemetry={setUiTelemetry} setSoapNote={setSoapNote} />
          </div>
        </section>

        <section style={styles.card}>
          <h2>Real-Time AI Telemetry</h2>
          <hr style={styles.divider} />
          
          <div style={styles.metricGroup}>
            <h3>Vocal Stress:</h3>
            <span style={{ ...styles.badge, backgroundColor: uiTelemetry.vocal_stress_level === 'Normal' ? '#10b981' : '#ef4444' }}>
              {uiTelemetry.vocal_stress_level}
            </span>
          </div>

          <div style={styles.metricGroup}>
            <h3>Automated Clinical Insights:</h3>
            <p style={styles.noteBox}>{uiTelemetry.doctor_note}</p>
          </div>

          {/* NEW: SOAP Note Dashboard Section */}
          <div style={styles.metricGroup}>
            <h3>Final SOAP Note:</h3>
            <div style={styles.soapBox}>
                {soapNote ? <pre style={{whiteSpace: 'pre-wrap'}}>{soapNote}</pre> : "Summary will appear here after call ends."}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

const styles = {
  // ... keep your existing styles, add these:
  soapBox: { backgroundColor: '#000', padding: '15px', borderRadius: '6px', color: '#fff', border: '1px solid #10b981', minHeight: '100px', fontSize: '14px' },
  container: { fontFamily: 'system-ui, sans-serif', backgroundColor: '#111827', color: '#f9fafb', minHeight: '100vh', padding: '20px' },
  header: { borderBottom: '1px solid #1f2937', paddingBottom: '15px', marginBottom: '30px' },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' },
  card: { backgroundColor: '#1f2937', borderRadius: '8px', padding: '20px', border: '1px solid #374151' },
  videoPlaceholder: { height: '300px', backgroundColor: '#374151', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', marginBottom: '15px' },
  badge: { padding: '6px 12px', borderRadius: '20px', fontWeight: 'bold', color: 'white' },
  noteBox: { color: '#a7f3d0', fontStyle: 'italic', marginBottom: '20px' },
  metricGroup: { marginBottom: '20px' }
};

export default App;