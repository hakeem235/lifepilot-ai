# Maestro E2E flows — LifePilot AI

UI end-to-end flows for the mobile app, driven with [Maestro](https://maestro.mobile.dev).
Maestro talks to the accessibility tree, so it reliably drives the React Native
Gesture Handler / Reanimated screens (paged onboarding, bottom sheet) that raw
`adb input` events do not.

## Flows

| File | What it does | Needs network / backend |
| --- | --- | --- |
| `smoke.yaml` | Launch → page through onboarding → reach the login screen. | No |
| `full-journey.yaml` | Onboarding → email sign-up + code verification → Home, Tasks (creates one), AI Chat, Insights, Profile (dark-mode toggle). | Yes |
| `subflows/*.yaml` | Building blocks included by the above via `runFlow`. Not run on their own. | — |

Screenshots land in `~/.maestro/tests/<timestamp>/` (and are named `01-onboarding`, `03-home`, …).

## Prerequisites

1. **Install Maestro** (not vendored): `curl -fsSL https://get.maestro.mobile.dev | bash`
2. **A running device/emulator with the native dev build installed.** Expo Go is
   not supported (it SIGSEGVs on this app's Hermes/RN combo — build natively):
   ```bash
   cd mobile
   JAVA_HOME=/path/to/jdk-21 npx expo run:android   # or run:ios on a Mac with Xcode
   ```
   Keep the Metro bundler it starts running.
3. **For `full-journey.yaml` only:**
   - Backend reachable at `localhost:8000` (Tasks/Insights persist there):
     ```bash
     cd backend && python manage.py runserver 0.0.0.0:8000
     adb reverse tcp:8000 tcp:8000      # emulator localhost -> host
     ```
   - Network access for Clerk (sign-up hits the live dev instance).
   - `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` set in `mobile/.env` (already required to build).

## Running

```bash
cd mobile
maestro test .maestro/smoke.yaml          # fast, offline-safe
maestro test .maestro/full-journey.yaml   # full authenticated drive-through
maestro test .maestro/                     # both (per config.yaml)
maestro studio                             # interactive: inspect selectors live
```

Override the sign-up credentials if needed:

```bash
maestro test -e PASSWORD='S3cret!' -e CODE='424242' .maestro/full-journey.yaml
```

## How auth works in the flow

- **Test email:** each run generates a unique `qa_<timestamp>+clerk_test@example.com`.
  The `+clerk_test` subaddress puts Clerk in test mode — no real email is sent and
  the verification code is always **`424242`** (`CODE`). Each run creates a real user
  in the Clerk **dev** instance; prune them periodically via the Clerk dashboard or
  `clerk` CLI.
- **Biometric gate:** after verification the app shows the tab shell. `BiometricGate`
  passes through automatically on devices with no enrolled biometrics (typical
  emulators). On a real device with Face ID / Touch ID enrolled, the OS prompt is
  native and Maestro cannot script it — disable biometric enrolment on the test
  device, or run on an emulator, for unattended runs.

## Notes

- `full-journey.yaml` targets the **dev build** (LogBox toasts may overlay in dev;
  they don't block Maestro's element taps). For pixel-clean screenshots, run a
  release build.
- CI wiring is intentionally omitted: Maestro E2E needs a live emulator/device
  (Maestro Cloud or an Android-emulator GitHub Action). Track that as a follow-up
  if we want these gating PRs.
