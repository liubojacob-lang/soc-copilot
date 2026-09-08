# Frontend Debug Scripts

This directory contains temporary Playwright-based debugging scripts for the Monitor page and related features. These scripts are not part of the production build or test suite.

## Scripts

| Script                    | Purpose                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------- |
| `check_history_times.mjs` | Analyze historical monitor data timestamps and time span.                             |
| `clear_cache.mjs`         | Clear browser `localStorage` on the Monitor page and verify cache reset.              |
| `debug_chart_errors.mjs`  | Inspect Recharts DOM structure and capture chart rendering errors/warnings.           |
| `debug_monitor.mjs`       | Open the Monitor page, capture console logs, network requests, and connection status. |
| `open_monitor.mjs`        | Open the Monitor page in a visible browser and keep it running for manual inspection. |
| `preview_monitor.mjs`     | Take a full-page screenshot of the optimized Monitor page.                            |
| `verify_sse.mjs`          | Verify the `/api/monitor/stream` SSE connection and data flow.                        |
| `verify_time_range.mjs`   | Test 1h/6h/24h time-range buttons on the Monitor page.                                |

## Usage

All scripts require a running frontend dev server (default `http://localhost:3003`) and Playwright:

```bash
cd frontend
node scripts/debug/verify_sse.mjs
```

## Notes

- These scripts launch Chromium (often in non-headless mode) and may leave the browser open.
- Screenshots are written to `/tmp/` by default.
- Prefer Playwright E2E tests under `frontend/e2e/` for automated regression coverage.
