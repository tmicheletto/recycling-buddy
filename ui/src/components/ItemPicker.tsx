import { useState, useMemo } from 'react';
import type { LabelCategory } from '../types/index.ts';
import './ItemPicker.css';

interface ItemPickerProps {
  categories: LabelCategory[];
  onSelect: (value: string) => void;
}

export function ItemPicker({ categories, onSelect }: ItemPickerProps) {
  const [query, setQuery] = useState('');

  const filteredCategories = useMemo(() => {
    if (!query.trim()) return categories;
    const lower = query.trim().toLowerCase();
    return categories
      .map((cat) => ({
        ...cat,
        items: cat.items.filter((item) =>
          item.display_name.toLowerCase().includes(lower)
        ),
      }))
      .filter((cat) => cat.items.length > 0);
  }, [categories, query]);

  const totalItems = filteredCategories.reduce(
    (sum, cat) => sum + cat.items.length,
    0
  );

  return (
    <div className="item-picker">
      <p className="picker-prompt">What is this item?</p>
      <input
        type="search"
        className="picker-search"
        placeholder="Search items..."
        aria-label="Search items"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div
        aria-live="polite"
        className="sr-only"
      >
        {query.trim() && `${totalItems} item${totalItems !== 1 ? 's' : ''} found`}
      </div>
      <div className="picker-list">
        {filteredCategories.length === 0 ? (
          <p className="picker-empty">No items match "{query}"</p>
        ) : (
          filteredCategories.map((cat) => (
            <div key={cat.category}>
              <h3 className="picker-category-heading">{cat.category}</h3>
              <div className="picker-items">
                {cat.items.map((item) => (
                  <button
                    key={item.value}
                    className="item-button"
                    onClick={() => onSelect(item.value)}
                  >
                    {item.display_name}
                  </button>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
