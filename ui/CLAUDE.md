# UI Component - CLAUDE.md

Guidance for working with the React frontend component of Recycling Buddy.

## Component Overview

React-based web interface for uploading images and viewing recycling classification results.

**Current Status**: Basic Vite + React + TypeScript scaffold. Needs custom components.

## Tech Stack

- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: CSS (consider adding TailwindCSS)
- **State Management**: React hooks (Context API if needed)
- **HTTP Client**: Fetch API (or add axios)

## Directory Structure

```
ui/
├── src/
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   ├── components/      # Reusable components (to be added)
│   │   ├── ImageUpload.tsx
│   │   ├── ResultsDisplay.tsx
│   │   └── RecyclingGuide.tsx
│   ├── hooks/           # Custom hooks (to be added)
│   │   └── useImageClassification.ts
│   ├── services/        # API client (to be added)
│   │   └── api.ts
│   ├── types/           # TypeScript types (to be added)
│   │   └── index.ts
│   └── App.css          # Styles
├── public/              # Static assets
├── Dockerfile
├── package.json
└── README.md
```

## Key Principles

1. **Type Safety**: Use TypeScript strictly, no `any` types
2. **Component Composition**: Build small, reusable components
3. **Hooks**: Use functional components with hooks
4. **Types**: Import types from `./types/`
5. **Error Handling**: Show user-friendly error messages

## Common Tasks

### Creating a New Component

**Functional component with TypeScript:**
```tsx
// src/components/ImageUpload.tsx
interface ImageUploadProps {
  onImageSelect: (file: File) => void;
  isLoading?: boolean;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({
  onImageSelect,
  isLoading = false
}) => {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onImageSelect(file);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        disabled={isLoading}
      />
    </div>
  );
};
```

### Calling the API

**Create API service:**
```typescript
// src/services/api.ts
import type { PredictionResponse } from '../types';

const API_URL = import.meta.env.API_URL || 'http://localhost:8000';

export const classifyImage = async (file: File): Promise<PredictionResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/predict`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
};
```

**Use in component:**
```tsx
import { classifyImage } from './services/api';
import { useState } from 'react';

const [result, setResult] = useState<PredictionResponse | null>(null);
const [error, setError] = useState<string | null>(null);

const handleImageSubmit = async (file: File) => {
  try {
    setError(null);
    const prediction = await classifyImage(file);
    setResult(prediction);
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Unknown error');
  }
};
```

### Custom Hooks

**Example: useImageClassification hook:**
```typescript
// src/hooks/useImageClassification.ts
import { useState } from 'react';
import { classifyImage } from '../services/api';
import type { PredictionResponse } from '../types';

export const useImageClassification = () => {
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const classify = async (file: File) => {
    setIsLoading(true);
    setError(null);

    try {
      const prediction = await classifyImage(file);
      setResult(prediction);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Classification failed');
    } finally {
      setIsLoading(false);
    }
  };

  return { result, isLoading, error, classify };
};
```

### Using Shared Types

**Import from shared directory:**
```typescript
// src/types/index.ts
export type {
  PredictionResponse,
  RecyclingCategory
} from '../types';
```

**Use in components:**
```tsx
import type { PredictionResponse } from '../types';

interface ResultsProps {
  result: PredictionResponse;
}

export const Results: React.FC<ResultsProps> = ({ result }) => {
  return (
    <div>
      <h2>Result: {result.label}</h2>
      <p>Confidence: {(result.confidence * 100).toFixed(1)}%</p>
    </div>
  );
};
```

## Styling

**Current setup:** Plain CSS

**Consider adding TailwindCSS:**
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Or use CSS modules for scoped styles:**
```tsx
// Component.module.css
import styles from './Component.module.css';

<div className={styles.container}>...</div>
```

## Environment Variables

**Create `.env` file:**
```
API_URL=http://localhost:8000
```

**Access in code:**
```typescript
const apiUrl = import.meta.env.API_URL;
```

**Note:** Vite exposes vars prefixed with `VITE_` or `API_` (configured in `vite.config.ts`)

## Form Handling

**Image upload with preview:**
```tsx
const [preview, setPreview] = useState<string | null>(null);

const handleFileSelect = (file: File) => {
  // Create preview
  const reader = new FileReader();
  reader.onloadend = () => {
    setPreview(reader.result as string);
  };
  reader.readAsDataURL(file);

  // Submit for classification
  classify(file);
};

return (
  <>
    <input type="file" onChange={(e) => {
      const file = e.target.files?.[0];
      if (file) handleFileSelect(file);
    }} />
    {preview && <img src={preview} alt="Preview" />}
  </>
);
```

## Error Handling

**Display user-friendly errors:**
```tsx
const ErrorMessage: React.FC<{ error: string }> = ({ error }) => (
  <div style={{ color: 'red', padding: '1rem', border: '1px solid red' }}>
    <strong>Error:</strong> {error}
  </div>
);

// Usage
{error && <ErrorMessage error={error} />}
```

## Loading States

**Show loading indicator:**
```tsx
{isLoading && <div>Classifying image...</div>}
{!isLoading && result && <Results result={result} />}
```

## Testing

**Add testing library:**
```bash
npm install -D @testing-library/react @testing-library/jest-dom vitest
```

**Example test:**
```tsx
// src/components/__tests__/ImageUpload.test.tsx
import { render, screen } from '@testing-library/react';
import { ImageUpload } from '../ImageUpload';

test('renders file input', () => {
  render(<ImageUpload onImageSelect={() => {}} />);
  const input = screen.getByRole('input', { type: 'file' });
  expect(input).toBeInTheDocument();
});
```

## Running Locally

```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

**Access app:** http://localhost:5173

## Vite Configuration

**Customize `vite.config.ts` if needed:**
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000', // Proxy API calls
    },
  },
});
```

## Accessibility

**Best practices:**
- Use semantic HTML (`<button>`, `<input>`, etc.)
- Add `alt` text to images
- Use proper heading hierarchy (`<h1>`, `<h2>`, etc.)
- Ensure keyboard navigation works
- Add ARIA labels where needed

**Example:**
```tsx
<button aria-label="Upload image" onClick={handleUpload}>
  Upload
</button>
```

## Performance

**Optimization tips:**
- Use `React.memo()` for expensive components
- Lazy load routes with `React.lazy()`
- Optimize images (compress, use WebP)
- Code splitting with dynamic imports

## Common Issues

### CORS Errors
- Check API CORS configuration
- Verify API URL in `.env` is correct
- Ensure API is running

### TypeScript Errors
- Run `npm run build` to check for type errors
- Ensure shared types are up to date
- Use proper type imports (not `import type`)

### Vite HMR Issues
- Restart dev server
- Clear `.vite` cache
- Check for circular dependencies

## Suggested Features to Build

1. **Image Upload Component**
   - Drag-and-drop support
   - Image preview
   - File validation (type, size)

2. **Results Display**
   - Show classification label
   - Display confidence score
   - Show all category probabilities (bar chart?)

3. **Recycling Guidance**
   - Based on classification, show recycling instructions
   - Icons for different material types
   - Links to local recycling resources

4. **History**
   - Show recent classifications (localStorage or backend)
   - Allow re-viewing past results

5. **Responsive Design**
   - Mobile-friendly interface
   - Touch-friendly upload

## Next Steps

1. Replace default Vite content in `App.tsx`
2. Create `ImageUpload` component with drag-and-drop
3. Create `Results` component to display classification
4. Set up API client in `services/api.ts`
5. Add error handling and loading states
6. Consider adding TailwindCSS for styling
7. Build out recycling guidance feature
