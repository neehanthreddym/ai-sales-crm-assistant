# Test and benchmark results

Measured on 2026-09-29 in the local project environment with Python 3.12.5.

## Automated tests

Command: `python3 -m pytest -q`

Latest result: **41 passed, 1 skipped, 0 failed in 0.53 seconds**.

The skipped test is the explicit credential-gated live workflow (`RUN_INTEGRATION_TESTS=true`). Unit tests mock external APIs and cover validation, deterministic urgency normalization, Groq strict-schema output, OpenAI SDK structured parsing, contact create/update, active-deal reuse, HubSpot and Sheets retry behavior, safe auth errors, pipeline/stage selection, stage rejection, association payload construction, note creation, Sheets insert/update/header behavior, service orchestration, partial Sheets failure and API routes.

## Offline benchmark

Command: `python3 scripts/benchmark.py --count 25`

Observed result from `artifacts/benchmark_results.json`:

| Metric | Measured value |
|---|---:|
| Requests | 25 |
| Successful local workflows | 25/25 (100%) |
| Median local end-to-end latency | 1.666 ms |
| p95 local end-to-end latency | 2.090 ms |
| Mock HubSpot failure count | 0 |
| Median deterministic mock-LLM latency | 0.025 ms |
| Mock Sheets synchronization | 25/25 (100%) |
| Duplicate requests | 6 |
| Duplicate prevention | 6/6 (100%) |
| Unique contacts / rows | 19 / 19 |

**Evidence boundary:** this benchmark measures Python orchestration using deterministic in-memory substitutes. It does not measure HubSpot, Groq, OpenAI, Google Sheets, network latency, production throughput, business impact, or service reliability.

## Live integrations

- HubSpot test-account validation on 2026-09-29: **9/9 checks passed** using `python scripts/verify_hubspot.py`.
  - Authentication
  - Contact create, retrieve and update
  - Duplicate detection
  - Deal creation
  - Contact-to-deal association
  - Deal-stage update
  - CRM note creation
- Groq validation on 2026-09-29: **3/3 checks passed** using `python scripts/verify_llm.py`.
  - Structured lead analysis
  - Validated urgency
  - Structured follow-up draft
- OpenAI structured generation with a real key/model: **Not yet measured.**
- Google Sheets validation on 2026-09-29: **5/5 checks passed** using `python scripts/verify_sheets.py`.
  - Authentication and read
  - Insert
  - Lookup
  - Update
  - Duplicate prevention
- Credential-gated live end-to-end workflow on 2026-09-29: **1/1 passed**.
  - Application-reported processing time: **6,163 ms**
  - Pytest wall time: **6.80 seconds**
  - Structured Groq analysis and follow-up generated
  - Existing synthetic HubSpot contact and active deal reused
  - A new CRM note was created and associated with the contact and deal
  - Google Sheets synchronization succeeded

The HubSpot, Groq, Google Sheets and end-to-end results record actual PASS reports produced against development/test services. The single live workflow is verification evidence, not a statistically meaningful performance benchmark.
