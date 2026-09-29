# Architecture

## Request path

1. FastAPI validates `LeadInput`; malformed values never reach an adapter.
2. `AIService` requests a Pydantic `LeadAnalysis` from the configured Groq or OpenAI adapter.
3. `CRMWorkflow` upserts a HubSpot contact by email.
4. It retrieves and validates the account's deal pipelines/stages.
5. It reuses a matching open associated deal or creates and associates one.
6. The selected LLM returns a Pydantic `FollowUpDraft`; no message is sent.
7. A HubSpot note is created and associated with both contact and deal using discovered association types.
8. `SheetsRepository` updates the row matching contact ID/email or appends one.
9. The route returns a typed response with timing and any Sheets warning.

## Boundaries

```text
app/api              HTTP validation and response mapping
app/services         use-case orchestration
app/models           transport-independent domain models
app/prompts          safety and task instructions
app/integrations     provider-specific HTTP/auth/schema logic
app/core             logging, exceptions and timing
```

Dependencies are constructed in `app/services/factory.py` and cached on FastAPI application state. Tests inject fakes or `httpx.MockTransport` without production fake modes.

## AI decision boundary

The model organizes intent, vehicle/budget context, summary and recommended action. Urgency is present in the structured model response but is normalized after parsing by an application-owned timing rubric: explicit immediate or 24–48-hour language is high, this-week or soon language is medium, and an absent qualifying timing signal is low. This hybrid boundary keeps CRM priority stable across repeated model calls while retaining AI assistance for unstructured content.

## Failure model

- Pydantic failures: FastAPI `422`, before side effects.
- Missing keys: safe `503 configuration_error`.
- HubSpot authentication/permission: safe `503`; upstream body is never exposed.
- CRM validation: `422 crm_validation_failed`.
- Groq/OpenAI timeout, rate limit, connection or schema failure: hard workflow failure.
- HubSpot timeout, `429`, or transient `5xx`: bounded exponential retry, then hard failure.
- Sheets failure after the CRM note: logged and returned as `partial_success`, with CRM IDs preserved.

This workflow is not a distributed transaction. A retry after a late failure relies on contact/deal/row idempotency. Each completed run deliberately writes a new note as an audit activity.

## Concurrency limitation

Contact search-then-create and Sheets read-then-write can race under concurrent identical requests. A production system should add an idempotency-key store/lock and use provider-supported unique-property upsert semantics where available.
