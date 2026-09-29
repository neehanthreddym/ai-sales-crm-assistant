# Resume evidence

## Verified functionality

- 41 mocked/unit/API tests passed; one credential-gated live test was skipped.
- Pydantic validation, Groq strict-schema and OpenAI SDK structured-output adapter behavior, HubSpot request construction, retries, association discovery/payloads, note creation, Sheets create/update behavior, orchestration and API routes passed tests.
- Live HubSpot test-account validation passed 9/9 checks: authentication; contact create, retrieve, update and duplicate detection; deal creation; contact-to-deal association; deal-stage update; and CRM note creation.
- Live Groq validation passed 3/3 checks: structured lead analysis, urgency validation and structured follow-up-draft generation.
- Live Google Sheets validation passed 5/5 checks: authentication/read, insert, lookup, update and duplicate prevention.
- The credential-gated live cross-service workflow passed 1/1 run, completing Groq analysis, HubSpot contact/deal reuse and note logging, and Google Sheets synchronization in an application-reported 6,163 ms.
- The offline 25-request orchestration benchmark completed and wrote `artifacts/benchmark_results.json`.

Live OpenAI operation remains unverified. OpenAI is an optional provider and is not required while Groq is configured.

## Verified metrics

- Automated tests: 41 passed, 0 failed, 1 skipped.
- HubSpot validation: 9/9 live test-account checks passed.
- Groq validation: 3/3 live checks passed.
- Google Sheets validation: 5/5 live checks passed.
- Live cross-service workflow: 1/1 passed at 6,163 ms application-reported processing time.
- Offline mocked benchmark: 25/25 successful local workflows; median 1.666 ms and p95 2.090 ms.
- Duplicate scenarios: 6/6 reused the in-memory contact/deal/row identity.

These are local engineering-test metrics, not external-service, production, customer, ROI or sales metrics.

## Technologies actually used

Python 3.12, FastAPI, Pydantic 2, httpx, OpenAI-compatible Python SDK transport, Groq and OpenAI structured-output adapters, HubSpot date-versioned REST API contracts, Google Auth, Google Sheets API v4 REST contracts, structlog, pytest, pytest-asyncio, Uvicorn and Docker.

## Interview demonstration

Follow [DEMO.md](DEMO.md). HubSpot, Groq, Google Sheets and the complete synthetic cross-service workflow can now be demonstrated against development/test services.

## Safe resume wording

- Built a FastAPI/Pydantic AI-assisted CRM POC with a date-versioned HubSpot integration, validating authentication and contact, deal, association, stage, duplicate-detection and note operations across **9 of 9 live test-account checks**.
- Implemented email/contact-ID idempotency across synthetic contact, deal and reporting-row workflows, confirming duplicate reuse in **6 of 6 offline benchmark duplicate scenarios**.
- Integrated Groq structured generation, HubSpot CRM operations and Google Sheets synchronization in a FastAPI POC, validating **1 of 1 live cross-service workflow run** at **6,163 ms application-reported processing time**.

Retain “POC,” “mocked,” or “local” qualifiers wherever the supporting evidence comes from local tests rather than live integrations.
