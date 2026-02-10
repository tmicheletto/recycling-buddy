import { useRef, useState } from 'react';
import { useImageUpload } from '../hooks/useImageUpload.ts';
import { useLabels } from '../hooks/useLabels.ts';
import './PhotoCapture.css';

type Phase = 'capture' | 'label' | 'uploading' | 'result';

export function PhotoCapture() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>('capture');
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const { error, result, upload, reset: resetUpload } = useImageUpload();
  const { categories, isLoading: labelsLoading, error: labelsError } = useLabels();

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
    setSelectedCategory(null);
    setPhase('label');
  }

  async function handleLabel(label: string) {
    if (!file) return;
    setPhase('uploading');
    await upload(file, label);
    setPhase('result');
  }

  function handleReset() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setSelectedCategory(null);
    resetUpload();
    setPhase('capture');
    if (inputRef.current) inputRef.current.value = '';
  }

  const activeCategory = categories.find((c) => c.category === selectedCategory);

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

      {phase === 'label' && previewUrl && (
        <div className="preview-container">
          <img src={previewUrl} alt="Captured photo" className="preview-image" />

          {labelsLoading && <p>Loading labels...</p>}
          {labelsError && <p className="label-error">Could not load labels: {labelsError}</p>}

          {!labelsLoading && !labelsError && !selectedCategory && (
            <div className="label-picker">
              <p className="picker-prompt">What is this item?</p>
              <div className="category-list">
                {categories.map((cat) => (
                  <button
                    key={cat.category}
                    className="category-button"
                    onClick={() => setSelectedCategory(cat.category)}
                  >
                    {cat.category}
                  </button>
                ))}
              </div>
            </div>
          )}

          {!labelsLoading && !labelsError && activeCategory && (
            <div className="label-picker">
              <button
                className="back-button"
                onClick={() => setSelectedCategory(null)}
              >
                &larr; {activeCategory.category}
              </button>
              <div className="item-list">
                {activeCategory.items.map((item) => (
                  <button
                    key={item.value}
                    className="item-button"
                    onClick={() => handleLabel(item.value)}
                  >
                    {item.display_name}
                  </button>
                ))}
              </div>
            </div>
          )}

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
