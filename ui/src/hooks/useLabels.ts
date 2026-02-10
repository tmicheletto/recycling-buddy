import { useEffect, useState } from 'react';
import { fetchLabels } from '../services/api.ts';
import type { LabelCategory } from '../types/index.ts';

export function useLabels() {
  const [categories, setCategories] = useState<LabelCategory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchLabels()
      .then((data) => {
        if (!cancelled) {
          setCategories(data.categories);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load labels');
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { categories, isLoading, error };
}
