# Lead Synchronizer

Small HTTP service that fetches source orders from `https://test.ooobs.ru/api/orders`, normalizes Russian phone numbers, merges duplicate phones, and returns deterministic JSON with synchronization statistics.

## Run

Requires Python 3.10+; no third-party dependencies.

```bash
python3 main.py
```

The service listens on `127.0.0.1:8001`. GET `/` returns the synchronized clients and statistics; GET `/health` performs the same source-backed check.

## Rules

- 10-digit Russian numbers receive the `7` country prefix.
- 11-digit numbers starting with `8` are converted to `7`; valid numbers are returned as `+7XXXXXXXXXX`.
- Invalid phone numbers are discarded.
- For each normalized phone, the record with the greatest amount wins; ties are resolved by the latest `created_at`.
- Results are computed from the source on each request and sorted by phone, so repeated requests against unchanged source data return the same result without persistent duplicate state.

No credentials are required or stored in the repository. If source authentication is introduced later, keep credentials in environment variables, never in source control.
