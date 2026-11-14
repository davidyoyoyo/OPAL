# OPAL

**Opinion research, made clear.**

OPAL is an account-free opinion research platform. A visitor asks a question, OPAL gathers and structures relevant evidence, and the visitor can inspect and export the resulting data.

## Current stage

The first commit establishes the public-facing website interface. The research preview is explicitly illustrative; no live research or statistical results are generated yet.

## Technology

- **Frontend:** Next.js 15, React 19 and TypeScript
- **Styling:** CSS
- **Icons:** Lucide
- **Planned research backend:** Python + FastAPI
- **Planned data processing:** Python, pandas and NumPy
- **Planned database:** PostgreSQL

Each part uses the technology best suited to its job. The frontend and research backend will communicate through a defined API.

## Run locally

Requirements: Node.js 20.9 or later.

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Product principles

- No accounts or registration.
- A question-first workflow.
- Survey measurements, expressed online opinions and supporting research remain distinct evidence types.
- Every result should be traceable to its sources.
- Statistical calculations are performed by conventional code, not guessed by an LLM.
- Users can export their results and leave.

## Roadmap

1. Website foundation and research request interface.
2. Research results workspace: tables, charts, filters and exports.
3. Python API and research orchestration.
4. Source connectors and permissions-aware evidence collection.
5. Structured evidence database, provenance and quality controls.
