# LifePilot AI

**Your Intelligent Daily Companion** — a mobile-first personal AI assistant that connects
email, calendar, tasks, notes, finance, and health, and works proactively to keep the day on
track. Powered by Anthropic Claude.

**Status:** 🔵 Phase 8 in progress — Issue 8.0 (scaffold + CI + design system).

## Structure

- `mobile/` — Expo / React Native app (TypeScript, Expo Router, NativeWind).
- `backend/` — Django 6 + DRF + PostgreSQL API.
- `design/LifePilot AI - Standalone.html` — design source of truth (decoded ✓).
- `docs/PRD.md` — product requirements (5 tabs + 4 detail features, phased MVP).
- `docs/ARCHITECTURE.md` — stack + system design (includes DECISION D1).
- `docs/DATABASE.md` — data model (MVP-real vs P2/P3 tables).

## Development

### Mobile app

```bash
cd mobile
cp .env.example .env   # fill in values
npm install
npm run ios            # or: npm start
```

Checks: `npm run typecheck` · `npm run lint`

### Backend

```bash
cd backend
cp .env.example .env   # fill in values
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Checks: `manage.py check` · `manage.py test`

## Design system

Tokens live in `mobile/tailwind.config.js` + `mobile/theme/` (brand indigo `#4F46E5`,
semantic light/dark surfaces, hero gradient). Screens compose from tokens and the
`mobile/components/ui/` kit (Card, Chip, Badge, Ring, ProgressBar, Fab) — never hardcode hex
values in screens.

## Integrations

Every integration sits behind the provider seam (`backend/core/providers/`): MVP ships
clearly-labeled mock data (`is_live=false`); P2/P3 register real providers under the same
names without touching UI. See `docs/ARCHITECTURE.md` §4.

## CI

GitHub Actions (`.github/workflows/ci.yml`): gitleaks · trufflehog · backend
`check --deploy` + tests (Postgres service) · mobile typecheck + lint.
