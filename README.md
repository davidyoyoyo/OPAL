# OPAL

**Opinion research, made clear.**

OPAL is an account-free opinion research platform. A visitor asks a question, OPAL searches connected evidence sources, and the visitor can inspect source records and export structured findings.

## Current stage

The frontend is connected to the Python research API. Scholarly discovery currently uses Crossref; the Eurostat connector discovers statistical datasets but does not yet retrieve opinion-survey distributions. OPAL therefore does not display measured public-opinion percentages yet. A separate survey-source registry and strict question-level survey schema are now in place, but no survey repository is registered until its access and reuse terms are suitable.

## Technology

- **Frontend:** Next.js, React and TypeScript
- **Backend API:** Python + FastAPI
- **Provider requests:** httpx
- **Research data processing:** Python (pandas / NumPy will be added when the analysis pipeline needs them)
- **Planned database:** PostgreSQL

## Run locally

Requirements: Node.js 20.9+ and Python 3.11+.

### 1. Start the research API

In Terminal:

```bash
cd OPAL/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API runs at http://127.0.0.1:8000. Its interactive documentation is at http://127.0.0.1:8000/docs.

### 2. Start the website

Open a second Terminal window:

```bash
cd OPAL
npm install
npm run dev
```

Open http://localhost:3000.

The website calls the local API by default. To use another API URL, copy `.env.example` to `.env.local` and change `NEXT_PUBLIC_OPAL_API_URL`.

## Adding a source

Scholarly providers get adapters under `backend/app/sources/providers/` and implement `SourceAdapter`. Survey repositories use a separate `SurveySourceAdapter` contract and `SurveySourceRegistry`, returning validated `SurveyQuestionResult` records. This keeps bibliographic discovery separate from measured opinion data.

See [the engine guide](backend/README.md) and [the architecture notes](docs/ENGINE_ARCHITECTURE.md).

## Duplicate-study handling

A study is the underlying research work; a source location is a website record that points to it. Multiple websites can therefore point to one study. Matching DOI identifiers are grouped under one study, while similar titles are flagged for review rather than silently merged. Separate survey waves remain separate evidence when their samples, dates or methods differ.

## Product principles

- No accounts or registration.
- A question-first workflow.
- Survey measurements, expressed online opinions and supporting research remain distinct.
- Every result should be traceable to its sources.
- Statistical calculations are performed by code, not guessed by an LLM.
- Users can export their results and leave.
