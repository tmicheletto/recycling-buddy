/**
 * Shared type definitions for recycling classification
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
