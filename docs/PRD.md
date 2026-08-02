# LifePilot AI — Product Requirements (PRD)

**Status:** ✅ Reconciled against `design/LifePilot AI - Standalone.html`
**Owner:** Ahmed · **Prepared by:** Strategic Advisor · **Date:** 2026-08-02
**Tagline (from design):** *Your Intelligent Daily Companion*

---

## 1. Executive Summary

**LifePilot AI** is a mobile-first personal AI assistant — an "everything companion" that
connects a user's email, calendar, tasks, notes, finances, and health, then works **proactively**
to keep their day on track. It summarizes, triages, schedules, drafts, nudges, and reports —
so the user carries less mental load.

**Positioning (from onboarding):** *"One companion that quietly keeps your day on track"* —
proactive, not just reactive: it reaches out *before* things slip (leave-now nudges, bill-due
alerts, forgotten-reply reminders).

## 2. Platform & Form Factor

The prototype is a **mobile app** (iOS device frame, iOS-26 "liquid glass" styling, Face ID,
"Continue with Apple", location/contacts permissions). This is a **native-feeling mobile
product**, not a desktop web dashboard. → See **DECISION D1** in ARCHITECTURE (React Native/Expo
vs mobile PWA). All screens below are phone screens.

## 3. Target Users

| Segment | Need |
|---------|------|
| Busy professionals | One place that summarizes the day and handles email/calendar noise |
| Overwhelmed multitaskers | Proactive nudges so nothing slips; less app-switching |
| Self-optimizers | Productivity insights, focus tracking, habit streaks, health/mood |

## 4. Information Architecture (from design)

**Pre-auth:** Splash → Onboarding (4 steps) → Login.
**App shell:** bottom nav with 5 tabs — **Home · Tasks · AI Chat · Insights · Profile**.
**Detail screens** (opened from Home → Explore): **Smart Planner · Email Assistant · Finance · Health**.

### 4.1 Onboarding (4 steps)
1. "Your AI Assistant for Everyday Life."
2. "Everything, organized automatically" — Emails triaged, Calendar synced, Tasks tracked, Notes captured, Expenses logged.
3. "Proactive, not just reactive" — leave-now / bill-due / forgot-to-reply examples.
4. "Permissions, on your terms" — Calendar, Email, Notifications, Location, Contacts (each gated, consent-first).

### 4.2 Login
SSO: **Apple, Google, Microsoft** + **Email** + **Face ID** (biometric unlock).

### 4.3 Home
- **AI Summary** hero card: e.g. "3 meetings, 2 urgent emails, a bill due tomorrow. Best focus window: 2–4 PM." + weather + traffic chips.
- Stat cards: Meetings today, Tasks due.
- **Quick Actions:** Add Task, Voice, Scan Doc, New Note, Reminder, Automate.
- **Explore** cards → Smart Planner, Email Assistant, Finance, Health.
- **Proactive nudge** card (e.g. "Leave now for your 10:30 meeting — traffic heavier than usual").
- **Voice FAB** (mic) — voice capture entry point.

### 4.4 Tasks
Segments: **Today / Upcoming / Completed**. Per-task priority badge (high/med/low), completion + progress. Add-task action.

### 4.5 AI Chat
Conversational assistant. Suggested prompts: *Summarize my emails, Plan my day, Generate shopping list, Reply to this email.* Voice waveform, camera + note attachments, free-text ("Ask LifePilot anything…").

### 4.6 Insights
Metrics: **Productivity score, Focus time, Tasks completed, Time saved by AI.** Weekly focus bar chart; **habit streak** ring (e.g. "12 days journaling").

### 4.7 Profile
Avatar/identity, **Dark Mode** toggle, and rows: Personalization, Connected accounts, Notifications, AI settings, **Subscription**, **Privacy Controls**.

### 4.8 Detail features
- **Smart Planner** — Day / Week / **Matrix (Eisenhower)** views; AI-scheduled focus blocks; "best focus window" suggestion.
- **Email Assistant** — inbox summary, urgent flagging, **one-tap AI reply**, summarize thread.
- **Finance** — monthly spend, category breakdown, **bill-due alerts**, **predicted spend**.
- **Health** — Water / Sleep / Steps rings, **mood check-in**, AI nudges (e.g. "a 20-min walk now…").

## 5. AI Capabilities (cross-cutting)

Daily summary generation · email triage & draft replies · smart scheduling / focus-window
detection · conversational assistant · spend prediction · health/mood suggestions · voice
capture · document scan (OCR) · automations. All powered by **Anthropic Claude** (+ tool/data
context per feature).

## 6. Integrations implied by the design

Email (Gmail/Outlook/Microsoft), Calendar, Notifications/push, Location & traffic, Weather,
Contacts, Finance/spend source, Health/steps (Apple Health / Google Fit), Voice (speech-to-text),
Document scan (OCR). **These are heavy** — see §8 phasing; most are **v2+**, mocked in MVP.

## 7. Monetization

Design includes a **Subscription** row in Profile → freemium with a paid tier is intended.
Recommend **free during validation**, subscription wired later. (Confirm with Ahmed.)

## 8. MVP Scope — recommended phasing (the full design is multi-phase)

The complete design is too large for one phase. Proposed slices:

**MVP (Phase 1) — the shell + core loop, AI real, integrations mocked:**
- Onboarding, Login (Email + one SSO), app shell + 5 tabs, light/dark.
- **Tasks** fully functional (CRUD, today/upcoming/completed, priority).
- **AI Chat** real (Anthropic), with suggested prompts operating on the user's tasks + a manual daily context.
- **Home** AI Summary generated from real tasks/calendar-stub; quick actions (Add Task, New Note real; Voice/Scan/Automate stubbed).
- **Insights** from real task/usage data (productivity score, tasks completed, streaks).
- Profile + settings + dark mode.
- Email/Finance/Health/Smart-Planner rendered with **clearly-labeled sample data** (visual parity, not wired).

**Phase 2:** Calendar + Email integration real (Smart Planner + Email Assistant live). Push nudges.
**Phase 3:** Finance + Health integrations, voice capture, document scan, automations, subscription/billing.

## 9. Decisions — RESOLVED (2026-08-02)

1. **Frontend platform:** ✅ **React Native + Expo** (native app).
2. **Auth:** ✅ **Clerk** (Apple/Google/Microsoft SSO + email; biometric unlock client-side).
3. **MVP scope:** ✅ **Lean shell + core loop** — Tasks + AI Chat + Insights real; Email/Finance/Health/Planner as clearly-labeled sample data; wired in P2/P3.
4. **Monetization:** free during validation (subscription wired later) — *default, confirm if changed.*
5. Single-user personal for MVP: yes.

---

## 10. Design tokens (from prototype)

- Brand/primary indigo `#4F46E5`; semantic: primary / secondary / accent / danger / warning / success; hero **gradient** (`--grad`).
- Light + dark themes. iOS-26 "liquid glass" device frame, rounded cards, chips, rings, progress tracks, bottom nav, FAB.
