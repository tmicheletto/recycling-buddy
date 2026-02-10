import { useRef, useState } from 'react';
import { useImageUpload } from '../hooks/useImageUpload.ts';
import type { UploadLabel } from '../types/index.ts';
import './PhotoCapture.css';

type Phase = 'capture' | 'preview' | 'uploading' | 'result';

export function PhotoCapture() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>('capture');
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const { error, result, upload, reset: resetUpload } = useImageUpload();

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
    setPhase('preview');
  }

  async function handleLabel(label: UploadLabel) {
    if (!file) return;
    setPhase('uploading');
    await upload(file, label);
    setPhase('result');
  }

  function handleReset() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    resetUpload();
    setPhase('capture');
    // Clear the input so the same file can be re-selected
    if (inputRef.current) inputRef.current.value = '';
  }

  return (
    <div className="photo-capture">
      <h1>Recycling Buddy</h1>

      {phase === 'capture' && (
        <>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="capture-input"
            id="photo-input"
            onChange={handleFileChange}
          />
          <label htmlFor="photo-input" className="capture-button">
            Take Photo
          </label>
        </>
      )}

      {phase === 'preview' && previewUrl && (
        <div className="preview-container">
          <img src={previewUrl} alt="Captured photo" className="preview-image" />
          <div className="label-buttons">
            <button
              className="label-button label-button--recyclable"
              onClick={() => handleLabel('recyclable')}
            >
              Recyclable
            </button>
            <button
              className="label-button label-button--not-recyclable"
              onClick={() => handleLabel('not_recyclable')}
            >
              Not Recyclable
            </button>
          </div>
          <button className="retake-button" onClick={handleReset}>
            Retake
          </button>
        </div>
      )}

      {phase === 'uploading' && previewUrl && (
        <div className="loading-overlay">
          <img src={previewUrl} alt="Uploading photo" className="preview-image" style={{ opacity: 0.5 }} />
          <div className="spinner" />
          <p>Uploading...</p>
        </div>
      )}

      {phase === 'result' && (
        <>
          {error ? (
            <div className="result-card result-card--error">
              <span className="result-icon">&#10007;</span>
              <p>{error}</p>
            </div>
          ) : result ? (
            <div className="result-card result-card--success">
              <span className="result-icon">&#10003;</span>
              <p>Uploaded as <strong>{result.label}</strong></p>
            </div>
          ) : null}
          <button className="another-button" onClick={handleReset}>
            Take Another Photo
          </button>
        </>
      )}
    </div>
  );
}
