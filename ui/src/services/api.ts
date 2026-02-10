import type { LabelsResponse, UploadResponse } from '../types/index.ts';

const API_URL = import.meta.env.API_URL || 'http://localhost:8000';

export async function fetchLabels(): Promise<LabelsResponse> {
  const response = await fetch(`${API_URL}/labels`);

  if (!response.ok) {
    throw new Error(`Failed to fetch labels (${response.status})`);
  }

  return response.json();
}

export async function uploadImage(
  imageBase64: string,
  label: string,
): Promise<UploadResponse> {
  const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64: imageBase64, label }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Upload failed (${response.status}): ${body}`);
  }

  return response.json();
}
