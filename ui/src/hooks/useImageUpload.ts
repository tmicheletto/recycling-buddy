import { useState } from 'react';
import { uploadImage } from '../services/api.ts';
import type { UploadResponse } from '../types/index.ts';

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Strip the data:...;base64, prefix — API expects raw base64
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}

export function useImageUpload() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  async function upload(file: File, label: string) {
    setIsLoading(true);
    setError(null);
    try {
      const base64 = await fileToBase64(file);
      const response = await uploadImage(base64, label);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsLoading(false);
    }
  }

  function reset() {
    setIsLoading(false);
    setError(null);
    setResult(null);
  }

  return { isLoading, error, result, upload, reset };
}
