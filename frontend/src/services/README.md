# Backend contract

The Research Assistant talks to the Python (FastAPI) backend in `/backend`. The Situation
Room endpoints below are **not built yet**; while `VITE_API_URL` is unset the Situation Room
uses built-in sample data.

To point the app at a different backend address, create a file named `.env` in the `frontend` folder:

```
VITE_API_URL=http://localhost:8000
```

Restart `npm.cmd run dev`. The AI provider's API key belongs on the backend only.
Never put it in the frontend.

## Situation Room

| Endpoint | Returns |
| --- | --- |
| `GET /api/countries` | `[{ id, name, region, position: [lat, lng], populationM, gdpB, indicators: { lifeExpectancy, renewableShare, internetUse } }]` |
| `GET /api/events` | `[{ id, countryId, category, severity, title, summary, occurredAt }]` |

`severity` is one of `low`, `moderate`, `high`, `critical`.

## Research Assistant

**Implemented.** The Research Assistant calls the FastAPI backend in `/backend`
(`http://localhost:8000` unless `VITE_API_URL` is set). The full request/response
contract, error codes and setup are documented in `backend/README.md`. Key points:

- `POST /api/research/ask` takes `{ question, conversation_id?, conversation_history? }`.
- Errors come back as `{ "error": { "code", "message", "request_id" } }`; the UI shows `message`.
- `GET /api/research/status` tells the UI whether the backend is configured.
- `researchService.js` converts the backend response into the shape the UI components use.
  Source links are accepted only if they start with `http://` or `https://`.
- The old pre-written answers in `data/researchDemo.js` are no longer used.
