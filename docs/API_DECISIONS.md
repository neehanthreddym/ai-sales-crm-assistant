# API decisions

Research date: 2026-09-29. Official provider documentation is the source of truth.

## HubSpot

Selected version: **`2026-09`**, the current stable date-based release. HubSpot introduced immutable date versions with an 18-month minimum support window and lists contacts, deals, notes, associations and pipelines among APIs updated for 2026-09. The application therefore uses:

```text
/crm/objects/2026-09/{objectType}
/crm/associations/2026-09/{from}/{to}/...
/crm/pipelines/2026-09/deals
```

The version is centralized in `HUBSPOT_API_VERSION` rather than scattered. Numerical `/crm/v3` or `/crm/v4` paths are intentionally absent. HubSpot's 2026-09 write paths also enforce portal-configured validation rules, so pipeline/stage configuration is read and validated before writes.

Association IDs are portal/direction sensitive. The client fetches `.../{from}/{to}/labels`, chooses a HubSpot-defined default, and passes its `typeId` in the date-versioned batch-create request's required `types` array.

Sources:

- [HubSpot date-based API versioning announcement](https://developers.hubspot.com/changelog/introducing-date-based-api-versioning)
- [HubSpot Fall 2026 API rollup](https://developers.hubspot.com/changelog/fall-2026-spotlight)
- [HubSpot migration playbook](https://developers.hubspot.com/blog/date-based-api-versioning-migration-playbook)
- [HubSpot 2026-09 CRM write validation](https://developers.hubspot.com/changelog/crm-api-write-validation-enforcement)

## LLM providers

The application uses a provider protocol selected by `LLM_PROVIDER`. Groq is the default; OpenAI remains available without code changes.

### Groq

Groq exposes an OpenAI-compatible endpoint at `https://api.groq.com/openai/v1`. The adapter uses the installed OpenAI-compatible async client, Groq Chat Completions, strict `json_schema` response formatting, and local Pydantic validation. The default model is the current production `openai/gpt-oss-20b`, which Groq documents as supporting strict structured outputs.

Sources: [Groq OpenAI compatibility](https://console.groq.com/docs/openai), [Groq structured outputs](https://console.groq.com/docs/structured-outputs), and [Groq supported models](https://console.groq.com/docs/models).

### OpenAI

When selected, the OpenAI adapter uses the current Python SDK's async Responses API and `responses.parse(..., text_format=PydanticModel)`. `output_parsed` is accepted only when non-null.

Source: [official openai-python structured output example](https://github.com/openai/openai-python/blob/main/examples/responses/structured_outputs.py) and [SDK parsing helpers](https://github.com/openai/openai-python/blob/main/helpers.md).

## Google Sheets

The integration uses Sheets API **v4** `spreadsheets.values.get`, `update` and `append`, with `RAW` input. Authentication requests only `https://www.googleapis.com/auth/spreadsheets`; no Drive-wide scope is needed because the operator creates/shares the spreadsheet separately.

Sources:

- [Sheets API v4 reference](https://developers.google.com/workspace/sheets/api/reference/rest)
- [Read and write values](https://developers.google.com/workspace/sheets/api/guides/values)
- [Append values method](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/append)
