import { useEffect, useState } from 'react';
import { fetchLabels } from '../services/api.ts';
import type { LabelItem } from '../types/index.ts';

export function useLabels() {
  const [items, setItems] = useState<LabelItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchLabels()
      .then((data) => {
        if (!cancelled) {
          setItems(data.items);
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

  return { items, isLoading, error };
}
