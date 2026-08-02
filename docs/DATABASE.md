# LifePilot AI — Data Model

**Status:** ✅ Reconciled against the prototype
**Date:** 2026-08-02

> Personal / single-tenant-per-user. Every row scoped to `user`; all querysets filter by the
> authenticated user. **Bold** tables are MVP-real; others back P2/P3 features (schema defined now,
> populated when the integration lands).

---

## MVP (real) tables

### **UserProfile**
| Field | Type | Note |
|-------|------|------|
| id | uuid pk | |
| auth_id | string | Clerk external id |
| email | string | |
| display_name | string | e.g. "Ahmed Khan" |
| avatar_initial | string | UI avatar |
| timezone | string | drives "today" + summary windows |
| theme | enum(light, dark) | Profile toggle |
| created_at | datetime | |

### **UserSettings** (Profile screen)
| Field | Type | Note |
|-------|------|------|
| user | fk → UserProfile (1:1) | |
| notifications_enabled | bool | |
| ai_settings | json | tone, autonomy level, model prefs |
| personalization | json | greeting, focus preferences |
| connected_accounts | json | provider → connected/scopes (P2+) |
| subscription_tier | enum(free, pro) | default free |

### **Task**
| Field | Type | Note |
|-------|------|------|
| id | uuid | |
| user | fk | |
| title | string | |
| notes | text | nullable |
| due_date | date | nullable; drives Today/Upcoming |
| priority | enum(high, medium, low) | badge |
| status | enum(open, done) | |
| progress | int (0–100) | progress track in UI |
| source | enum(manual, ai, email, scan) | provenance |
| created_at / completed_at | datetime | |

### **Note** (Quick Actions → New Note; chat attach)
| id | uuid | · | user fk | · | title string | · | body text | · | created_at |

### **CopilotMessage** (AI Chat history)
| Field | Type | Note |
|-------|------|------|
| id | uuid | |
| user | fk | |
| role | enum(user, assistant) | |
| content | text | |
| context_ref | json | what context bundle was sent (audit) |
| created_at | datetime | |

### **DailySummary** (Home AI Summary hero)
| Field | Type | Note |
|-------|------|------|
| id | uuid | |
| user | fk | |
| date | date | unique(user, date) |
| summary_text | text | AI-generated |
| best_focus_window | string | e.g. "2–4 PM" |
| meeting_count / task_due_count | int | stat cards |
| generated_by | enum(ai, fallback) | degradation flag |

### **HabitStreak / Insight metrics**
Insights (productivity score, focus time, tasks completed, time saved, weekly focus, streaks)
are **derived** from Task + usage events for MVP — no dedicated store beyond:

**UsageEvent**
| id | uuid | user fk | type enum(focus_session, task_done, ai_action, journal) | value int | occurred_at datetime |

**Habit** (streaks, e.g. "12 days journaling")
| id | uuid | user fk | title string | cadence enum(daily,weekly) | active bool |
**HabitLog** | id | habit fk | date | completed bool | unique(habit, date) |

---

## P2 / P3 tables (schema now, populated when integration lands)

### CalendarEvent (P2 — Smart Planner)
| id | user fk | external_id | title | start/end datetime | source enum(google,microsoft,manual) | ai_scheduled bool | quadrant enum(do,schedule,delegate,delete) `Matrix view` |

### EmailItem (P2 — Email Assistant)
| id | user fk | external_id | from_name | subject | snippet | is_urgent bool | is_read bool | received_at | ai_draft_reply text nullable |

### ConnectedAccount (P2 — OAuth)
| id | user fk | provider enum(google,microsoft,apple,...) | scopes json | access/refresh tokens (encrypted) | status | connected_at |

### Transaction + SpendCategory (P3 — Finance)
Transaction | id | user fk | amount | category fk | occurred_at | merchant | source |
SpendCategory | id | user fk | name | color | monthly_budget |
BillReminder | id | user fk | label | amount | due_date | autopay bool |

### HealthMetric (P3 — Health)
| id | user fk | date | metric enum(water,sleep,steps) | value | goal | source enum(apple_health,google_fit,manual) |
MoodCheckin | id | user fk | date | mood int(1–5) |

### Automation (P3 — Quick Actions → Automate)
| id | user fk | name | trigger json | action json | enabled bool |

---

## Notes
- JSON columns (`ai_settings`, `connected_accounts`, `context_ref`, automation trigger/action) are
  MVP-flexible; normalize if they harden.
- OAuth tokens **encrypted at rest**, least-scope, consent-first (onboarding step 4).
- Privacy Controls → build user data **export + delete** paths early.
