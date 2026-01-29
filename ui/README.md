# UI Component

React frontend for the Recycling Buddy application.

## Overview

This component provides:
- Image upload interface
- Classification results display
- User-friendly recycling guidance

## Tech Stack

- React 18+
- TypeScript
- Vite (build tool)
- TailwindCSS (to be added)

## Directory Structure

```
ui/
├── src/
│   ├── App.tsx          # Main application component
│   ├── main.tsx         # Application entry point
│   ├── components/      # Reusable components (to be added)
│   ├── hooks/           # Custom hooks (to be added)
│   ├── services/        # API client (to be added)
│   └── types/           # TypeScript types (to be added)
├── public/              # Static assets
├── Dockerfile           # Container configuration
└── package.json         # Node dependencies
```

## Setup

```bash
cd ui
npm install
```

## Development

```bash
# Run locally
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run with Docker
docker build -t recycling-buddy-ui .
docker run -p 5173:5173 recycling-buddy-ui
```

## Environment Variables

Create a `.env` file:

```
VITE_API_URL=http://localhost:8000
```

## Features

- Image upload with drag-and-drop
- Real-time classification results
- Material identification guidance
- Responsive design

## Testing

```bash
npm test
```

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.
