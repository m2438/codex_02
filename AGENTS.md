# AGENTS.md

## Project purpose
This repository is a demo application for CRE sales intelligence.
The app helps users identify large listed companies that may have CRE strategy needs by collecting IR documents, extracting CRE-related signals, scoring sales priority, and showing results in a browser dashboard.

## Language and audience
- UI labels and reports should be in Japanese.
- The assumed users are CRE consultants, PM/CM consultants, and enterprise sales teams.
- Explanations must be suitable for client-facing business documents.

## Technical stack
- Frontend: Next.js + React + TypeScript
- Backend: FastAPI + Python
- Database: SQLite for demo, designed to be replaceable by PostgreSQL
- AI: OpenAI API, with mock mode when API key is unavailable
- Charts: Recharts
- Deployment: Docker Compose

## Data policy
- Use public IR documents or sample documents only.
- Do not hard-code confidential client data.
- Every AI-generated CRE signal must include evidence text and source document reference.
- If evidence is insufficient, mark the signal as low confidence.

## Development rules
- Keep the demo simple and runnable locally.
- Provide seed data so the dashboard works immediately.
- Add tests for scoring logic and API response formats.
- Update README with setup, environment variables, and demo scenario.