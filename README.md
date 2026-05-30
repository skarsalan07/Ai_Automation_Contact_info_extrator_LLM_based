# Prospect Research Agent

An AI-powered B2B prospect-research pipeline. Give it a company website URL, and it returns a structured `CompanyProfile` — company name, contact details, core service, target customer, probable pain point, and a tailored outreach opener.

Built for the hackathon spec: **Colab notebook + FastAPI backend + React frontend + SQLite persistence + Groq llama-3.3-70b**, with strict anti-hallucination guards and graceful failure on unseen / broken / Cloudflare-protected websites.

---

## Architecture

```
prospect-agent/
├── notebook/
│   └── prospect_research_agent.ipynb     # judge-runnable Colab notebook
├── backend/                              # FastAPI service
│   ├── main.py                           # app entrypoint
│   ├── config.py                         # pydantic-settings
│   ├── routers/                          # /enrich, /results
│   ├── services/                         # scraper, extractor, llm, pipeline
│   ├── models/                           # SQLAlchemy ORM
│   ├── schemas/                          # Pydantic models (CompanyProfile)
│   ├── database/                         # SQLite engine + session
│   └── utils/                            # logger + HTTP fallback chain
├── frontend/                             # React + Vite UI
│   └── src/
│       ├── pages/Home.jsx
│       └── components/                   # form, card, table, toast, skeleton, etc.
├── render.yaml                           # backend deploy (Render)
├── Procfile                              # fallback Procfile
└── frontend/vercel.json                  # frontend deploy (Vercel)
```

### Enrichment pipeline (high level)

1. **Discovery** — fetch homepage, read `robots.txt`, parse `sitemap.xml` (incl. nested sitemap-index), extract internal `<a>` links.
2. **Ranking** — score every candidate URL against priority keywords (`about`, `services`, `contact`, `team`, etc.) using **RapidFuzz** partial_ratio; visit only the top `MAX_PAGES_PER_SITE` pages.
3. **Fetch** — fallback chain **`requests` → `requests.Session` → `cloudscraper`**, with User-Agent rotation, exponential-backoff retries via `tenacity`, and per-strategy timeouts.
4. **Clean** — strip scripts/styles/nav/forms/iframes, dedupe lines, cap to ~2,800 words (`MAX_CONTEXT_WORDS`).
5. **Extract** — emails / phones via regex, address via JSON-LD `PostalAddress` → `<address>` tag → footer heuristics, company name via OG / JSON-LD / title / logo-alt / domain fallback.
6. **Insights** — Groq `llama-3.3-70b-versatile` with `response_format=json_object` and a strict prompt: *use only the provided text, return Unknown for missing facts, never invent contacts.*
7. **Anti-hallucination guard** — every email / phone / address returned is cross-checked against the raw scraped text and dropped if it didn't actually appear there.
8. **Pydantic validation** — `CompanyProfile` coerces `null`/missing fields to `""` or `[]`. Schema is **never** broken.

---

## Strict output schema

Every enrichment — successful, partial, or failed — returns:

```json
{
  "website_name": "",
  "company_name": "",
  "address": "",
  "mobile_number": "",
  "mail": [],
  "core_service": "",
  "target_customer": "",
  "probable_pain_point": "",
  "outreach_opener": ""
}
```

Missing fields are `""` or `[]`. Never `null`. Never broken.

---

## 1 · Run the Colab notebook (judges)

1. Open [`notebook/prospect_research_agent.ipynb`](notebook/prospect_research_agent.ipynb) in [Google Colab](https://colab.research.google.com/).
2. In Cell 2, set your `GROQ_API_KEY` (a default is included for the hackathon; replace with your own for production).
3. **Run All**. Cell 10 contains the judge-input list:
   ```python
   URLS = [
       "https://www.stripe.com",
       "https://www.notion.so",
   ]
   ```
   Edit it (or uncomment the `input()` prompt to paste a JSON array interactively), then re-run the final cell.
4. Output: a JSON array printed in the cell + saved to `results.json`.

The notebook is fully self-contained — no imports from the backend package.

---

## 2 · Run the FastAPI backend locally

```bash
cd prospect-agent
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env                # then edit GROQ_API_KEY
uvicorn backend.main:app --reload --port 8000
```

Open <http://localhost:8000/docs> for the interactive Swagger UI.

### Endpoints

| Method | Path       | Body / Query                         | Returns                       |
|-------:|------------|---------------------------------------|-------------------------------|
| GET    | `/`        | —                                     | `{ "status": "ok", ... }`     |
| GET    | `/health`  | —                                     | `{ "status": "ok" }`          |
| POST   | `/enrich`  | `{ "url": "...", "website_name": "?" }` | `CompanyProfile`              |
| GET    | `/results` | `?limit=100&offset=0`                  | `CompanyProfile[]` (stored)   |

#### Example

```bash
curl -X POST http://localhost:8000/enrich \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://www.stripe.com"}'
```

---

## 3 · Run the React frontend locally

```bash
cd frontend
cp .env.example .env                     # adjust VITE_API_BASE_URL if backend is elsewhere
npm install
npm run dev                              # http://localhost:5173
```

UI features:

- **Enrichment form** — `Website Name` (optional) + `Website URL`.
- **Live loading** — spinner, animated progress bar, skeleton placeholders.
- **Result card** — every schema field with empty-state fallbacks; email list renders as pills.
- **Show All Results** — paginated SQLite-backed table.
- **Toast notifications** — success / error feedback that auto-dismiss.
- **Error boundary** — catches render-time crashes and offers a reset.

---

## 4 · Deployment

### Backend on Render

1. Push this repo to GitHub.
2. In Render, create a new **Web Service**, point it at the repo.
3. Render will pick up `render.yaml`. Set the `GROQ_API_KEY` secret in the Render dashboard.
4. Build command: `pip install -r backend/requirements.txt`. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.

### Frontend on Vercel

1. Import the repo in Vercel; set the **Root Directory** to `frontend/`.
2. `vercel.json` is already configured (Vite framework, SPA rewrite).
3. Add an env var `VITE_API_BASE_URL` pointing at your Render backend URL (e.g. `https://prospect-agent-backend.onrender.com`).
4. Update the backend's `CORS_ORIGINS` env var to include the Vercel domain.

---

## 5 · Environment variables

Backend (`backend/.env`):

| Var                  | Default                                 | Purpose                                  |
|----------------------|------------------------------------------|------------------------------------------|
| `GROQ_API_KEY`       | _(required)_                             | Groq API key.                            |
| `GROQ_MODEL`         | `llama-3.3-70b-versatile`                | Groq chat model id.                      |
| `DATABASE_URL`       | `sqlite:///./data/prospects.db`          | SQLAlchemy URL.                          |
| `CORS_ORIGINS`       | `http://localhost:5173,http://localhost:3000` | Comma-separated allowlist.          |
| `LOG_LEVEL`          | `INFO`                                   | Python logging level.                    |
| `REQUEST_TIMEOUT`    | `20`                                     | HTTP timeout per fetch attempt (s).      |
| `MAX_PAGES_PER_SITE` | `6`                                      | Cap on pages fetched per company.        |
| `MAX_CONTEXT_WORDS`  | `2800`                                   | Word cap on text sent to the LLM.        |

Frontend (`frontend/.env`):

| Var                  | Default                  | Purpose                  |
|----------------------|---------------------------|--------------------------|
| `VITE_API_BASE_URL`  | `http://localhost:8000`   | Backend base URL.        |

---

## 6 · Hackathon resilience checklist

| Scenario                  | Behavior                                                                 |
|---------------------------|--------------------------------------------------------------------------|
| Unseen URL                | Default pipeline runs; ranking adapts via fuzzy matching.                |
| No `sitemap.xml`          | Falls back to homepage `<a>` link extraction.                            |
| No contact page           | Contacts pulled from any fetched page (homepage, footer).                |
| Cloudflare-protected page | Fallback chain ends in `cloudscraper`.                                   |
| Slow / 5xx site           | Tenacity exponential-backoff retries; strategy then steps to next.       |
| Broken HTML               | BeautifulSoup with `lxml` is permissive; bad JSON-LD is repaired.        |
| No structured data        | Address heuristic on cleaned text; company name from title / logo alt.   |
| LLM error or rate limit   | Insight fields returned as `""`; schema still valid.                     |
| Missing field             | Pydantic coerces to `""` / `[]`; never `null`.                           |
| Total scrape failure      | Returns a valid `CompanyProfile` with only `website_name` populated.     |

The application **never crashes** and **never breaks schema**.
