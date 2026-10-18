# Chat correction — 2026-10-18

Scope: finish PR #8 chat diagnostics without changing the statistical engine or production.

## Changes
- Detect GPT configuration pointing to Gemini endpoint and missing OpenAI credentials before calling provider.
- Remove unconditional temperature; official OpenAI GPT-6 short descriptive requests use reasoning_effort=none and bounded completion tokens.
- Identify HTTP 400/401/403/404/429, timeout, unavailable provider and empty response with safe codes. Never expose provider error bodies.
- Display fallback reason in Italian; retain compatibility with legacy backend responses.
- Add provider contract tests and browser chat failure/recovery checks.

## Verification at commit preparation
- Backend: 37 tests passed (mocked model provider; no live model credentials accessed).
- Frontend: 25 tests passed; Vite production build passed.
- git diff --check passed.
- Local browser run could not launch: Chromium/WebKit executables missing. CI installs both and runs the updated eight browser cases; consult the exact commit's Actions result.

## Deployment gate and remaining limits
Render latest deployment inspected: dep-db8jf1ivcj2c73cmr63g, live on commit 2fff9ae2cce21004eff4b1a3f1b0ce7419fbfb59. Branch before this change: d74f6c5aa447f87d0f44d0fdf019ad5ce8c94bda. No merge, production deployment, secrets or databases changed.

These contract tests do not establish that the user's model account is reachable or funded. Live chat must be tested against a backend running the corrected code before release. Preview frontend continues to proxy the old production backend; it cannot prove new backend behavior. A configured provider name is not proof of successful generation.

Live events, lineups, cloud archive/backup, notifications and scheduled reports are not completed by this change. OAuth and email remain deferred by user request. OpenFootball is a data provider, not a database.

Rollback: branch change can be reverted independently; production remains untouched. Before any release record both current deployment IDs, deploy a tested backend candidate and frontend preview, verify real fixtures/chat, then promote only after the release gate. See FINAL_QA_2026_10_15.md and REGRESSION_VERIFICATION_PR7.md for previous browser evidence and rollback details.
