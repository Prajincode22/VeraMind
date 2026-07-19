import React, { useState } from 'react';

export default function VideoUploader() {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    setStatus('Uploading video file to backend AI...');

    try {
      const response = await fetch('http://localhost:8000/api/upload-video', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setStatus('Processing analysis pipeline. Look at your Doctor HUD Dashboard!');
    } catch (error) {
      console.error('Upload failed:', error);
      setStatus('Upload failed. Verify backend connectivity.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ padding: '20px', border: '2px dashed #374151', borderRadius: '8px', textAlign: 'center', backgroundColor: '#1f2937', color: '#fff' }}>
      <h3 style={{ margin: '0 0 10px 0', fontSize: '16px' }}>Test Simulation Controller</h3>
      <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '15px' }}>
        Upload a pre-recorded session file (.mp4) to evaluate multi-modal sensor fusion outputs.
      </p>
      <input 
        type="file" 
        accept="video/*" 
        onChange={handleFileChange} 
        disabled={uploading}
        style={{ display: 'none' }}
        id="video-upload-input"
      />
      <label 
        htmlFor="video-upload-input" 
        style={{ display: 'inline-block', padding: '8px 16px', backgroundColor: uploading ? '#4b5563' : '#2563eb', color: '#fff', borderRadius: '4px', cursor: uploading ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '14px' }}
      >
        {uploading ? 'Processing File...' : 'Select Session Video'}
      </label>
      {status && <div style={{ marginTop: '12px', fontSize: '13px', color: '#34d399' }}>{status}</div>}
    </div>
  );
}