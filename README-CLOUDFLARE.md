# OxyZen — Cloudflare deployment

This package is prepared for:

- React frontend → Cloudflare Workers Static Assets
- FastAPI backend → Docker service (Render/Railway/Fly/etc.)
- MongoDB → MongoDB Atlas
- Existing Emergent LLM integration → `EMERGENT_LLM_KEY`

The Cloudflare Worker proxies `/api/*` to the FastAPI backend, so the browser uses a same-origin API and does not need `REACT_APP_BACKEND_URL`.

## Cloudflare

1. Install Node.js LTS.
2. From the project root:
   `npm install`
3. Build:
   `npm run build`
4. Log in:
   `npx wrangler login`
5. Configure the backend URL as a Worker secret/variable:
   `npx wrangler secret put BACKEND_URL`
   Enter the FastAPI URL, e.g. `https://oxyzen-api.example.com`
6. Deploy:
   `npx wrangler deploy`

## Backend environment variables

Set these on the backend service:

- `MONGO_URL`
- `DB_NAME=oxyzen`
- `JWT_SECRET`
- `EMERGENT_LLM_KEY`
- `AI_MODEL_PROVIDER=gemini`
- `AI_MODEL_NAME=gemini-3-flash-preview`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

## MongoDB Atlas

Create a database named `oxyzen`. The application creates its collections and indexes at startup. Allow the backend service to connect to the cluster and create a database user with read/write access.

## Important

Do not put MongoDB credentials, JWT secrets, or the Emergent key into the React frontend. They belong only in backend environment variables or Cloudflare Worker secrets.
## Global city search

OxyZen now uses the Open-Meteo Geocoding API server-side for location search. The existing curated catalogue remains the fast first source, while global geocoding results are merged and cached for 10 minutes. No frontend API key is required. The AQI engine still uses OxyZen's deterministic AQI model for the selected coordinates.
