/**
 * Type definitions for recycling classification
 */

export interface PredictionResponse {
  label: string;
  confidence: number;
  categories: CategoryScore[];
}

export interface CategoryScore {
  [category: string]: number;
}

export type RecyclingCategory = 'recyclable' | 'non-recyclable' | 'compost';

export interface HealthResponse {
  status: string;
  version: string;
}

export type UploadLabel = 'recyclable' | 'not_recyclable';

export interface UploadRequest {
  image_base64: string;
  label: UploadLabel;
}

export interface UploadResponse {
  success: boolean;
  s3_key: string;
  label: string;
}
