# Deloitte Search - Frontend

Next.js 16 (App Router) frontend for the AI-driven company-wide search engine.

## Tech Stack

- **Framework:** Next.js 16.1.6 (App Router, React 19)
- **UI:** shadcn/ui (@base-ui/react primitives) + Tailwind CSS 4
- **Icons:** lucide-react
- **Font:** Geist (Google Fonts, optimized via next/font)
- **Package Manager:** Bun (Docker), npm (local)

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page with search bar and example queries |
| `/search` | Search results with filter sidebar (category, doc type, latest-only toggle) |
| `/admin/upload` | Document upload portal with drag-and-drop |

## Components

- `search-bar.tsx` - Search input with URL-based navigation and search tips popup
- `result-card.tsx` - Document result display with version badge, category, metadata
- `filter-panel.tsx` - Sidebar filters (latest-only toggle, category, file type)
- `file-upload.tsx` - Drag-and-drop file uploader with progress indicators
- `search-tips.tsx` - Popup with example search queries

## API Client

`lib/api.ts` connects to the backend via `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`):

- `POST /api/search` - Hybrid search with filters
- `GET /api/documents` - List ingested documents
- `POST /api/documents` - Upload a document (multipart form)

## Development

```bash
bun install
bun run dev       # Dev server on :3000
bun run build     # Production build
bun run lint      # ESLint
```

Or via Docker Compose from the repo root:

```bash
docker compose up frontend
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |
