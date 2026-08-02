# LifePilot AI — Architecture

**Status:** ✅ Reconciled against the prototype
**Date:** 2026-08-02

---

## DECISION D1 — Frontend platform ✅ DECIDED (2026-08-02)

**Ahmed's call: React Native + Expo.** The app is a true native mobile build (matching the
prototype's iOS frame, Face ID, Apple sign-in, native integrations). Backend stays house-standard
(Django/DRF + Postgres). Auth: **Clerk**. MVP: **lean shell + core loop** (see PRD §8 Phase 1).

## 1. Stack

| Layer | Choice | Note |
|-------|--------|------|
| Mobile app | **React Native + Expo** (TypeScript) | Pending D1. Expo Router, NativeWind (Tailwind-for-RN) to mirror the design tokens |
| Backend | **Django 6 + DRF + PostgreSQL** | House standard — reuse ComplianceAI/Mizan scaffolding |
| AI | **Anthropic Claude** | Opus for chat/reasoning; a cheaper model for routine summaries |
| Auth | **Clerk** (Apple/Google/Microsoft SSO + email; biometric unlock client-side) | Pending the platform auth decision; Clerk covers the SSO set the design shows |
| Async/jobs | Celery + Redis (or Django-Q) | Proactive nudges, summary generation, integration polling |
| Push | Expo Push Notifications | Proactive nudges (P2) |
| Deploy | Backend on **Render** (+ managed Postgres, Redis); app via **EAS Build** / TestFlight | Reuse `render.yaml` blueprint pattern |
| CI | GitHub Actions — gitleaks + trufflehog + backend check/tests + app typecheck/lint | Reuse existing workflow |

## 2. System Shape

```
[ Expo / React Native app ]
        │  DRF REST + JWT (Clerk)
        ▼
[ Django / DRF API (Render) ] ──▶ [ PostgreSQL ]
        │           │
        │           ├─▶ [ Redis + Celery ]  proactive nudges, summaries, integration sync
        │           └─▶ [ Anthropic Claude ]  summary / chat / triage / predictions
        │
        └─▶ External integrations (phased): Gmail/Outlook · Google/Microsoft Calendar ·
             Weather · Maps/traffic · Finance source · Health (Apple Health/Google Fit) ·
             Speech-to-text · OCR
```

## 3. AI Layer

- **Context bundles, never raw dumps.** Each feature builds a compact, typed context (today's
  tasks, calendar stub, recent email metadata) and passes it to Claude. Summaries and chat share
  one `ai/` service module (single source of truth), mirroring ComplianceAI's `billing/usage.py` pattern.
- **Graceful degradation:** every AI call has a deterministic fallback so the app is usable if
  the model call fails (e.g. Home shows a rule-based summary).
- **Model split:** Opus for AI Chat + planning reasoning; cheaper model for routine daily summaries.

## 4. Integration Strategy (phased — matches PRD §8)

- **MVP:** integrations **mocked** behind a provider interface with clearly-labeled sample data.
  Real, working: Tasks, AI Chat, Insights (from real task/usage data), Home summary from real tasks.
- **P2:** Calendar + Email providers implemented behind the same interfaces (Smart Planner + Email Assistant go live). Push nudges.
- **P3:** Finance, Health, voice (STT), document scan (OCR), automations, subscription/billing.

Every integration sits behind a `providers/` seam so MVP mocks swap to real without touching UI.

## 5. Security / Governance

- No secrets in git; env-only (`ANTHROPIC_API_KEY`, `DATABASE_URL`, Clerk keys, provider keys) with `sync:false` in `render.yaml`.
- OAuth tokens for email/calendar/health encrypted at rest; least-scope, consent-first (matches onboarding step 4).
- Prod hardening gated on `DEBUG=false` (reuse ComplianceAI settings pattern).
- gitleaks + trufflehog pre-push; **report any new dependency/integration/API key before commit** (governance).
- Privacy Controls screen implies user data export/delete — plan for it early (GDPR-friendly).

## 6. Design System

- Tokens from the prototype: primary `#4F46E5`, semantic secondary/accent/danger/warning/success, hero gradient; light + dark.
- Rebuild as NativeWind theme tokens + a small component kit (card, chip, badge, ring, progress, bottom-nav, FAB) so screens compose from tokens, not hardcoded values.

## 7. Decisions Needed Before Build

1. **D1 — Expo/React Native vs Next.js PWA** (recommend Expo).
2. **Auth — Clerk vs first-party**, and first SSO provider (recommend Clerk).
3. **Confirm MVP mock/real integration line** (PRD §8).
4. **AI model tiering** (Opus chat / cheaper summaries).
