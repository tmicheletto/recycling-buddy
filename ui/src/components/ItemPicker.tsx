import { useState, useMemo } from 'react';
import type { LabelItem } from '../types/index.ts';
import './ItemPicker.css';

interface ItemPickerProps {
  items: LabelItem[];
  onSelect: (value: string) => void;
}

export function ItemPicker({ items, onSelect }: ItemPickerProps) {
  const [query, setQuery] = useState('');

  const filteredItems = useMemo(() => {
    if (!query.trim()) return items;
    const lower = query.trim().toLowerCase();
    return items.filter((item) =>
      item.display_name.toLowerCase().includes(lower)
    );
  }, [items, query]);

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
        {query.trim() && `${filteredItems.length} item${filteredItems.length !== 1 ? 's' : ''} found`}
      </div>
      <div className="picker-list">
        {filteredItems.length === 0 ? (
          <p className="picker-empty">No items match "{query}"</p>
        ) : (
          <div className="picker-items">
            {filteredItems.map((item) => (
              <button
                key={item.value}
                className="item-button"
                onClick={() => onSelect(item.value)}
              >
                {item.display_name}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
