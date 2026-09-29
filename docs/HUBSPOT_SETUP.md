# HubSpot test-account setup

Use synthetic data only. HubSpot UI names change over time, so follow the linked current developer documentation when a label differs.

1. Create a HubSpot developer account and a developer test account from the developer portal. Do not connect a real dealership portal.
2. In the test account, create a Developer Platform app/service key or OAuth app appropriate for a single-account test integration. HubSpot 2026.09 identifies service keys as the successor path for scoped in-account integrations; OAuth remains appropriate when an app is installed by users.
3. Grant the minimum CRM permissions needed to read/write contacts, deals and notes and to read deal pipelines/association definitions. In scope names this generally includes contact, deal and note read/write scopes. Confirm the exact scope names in the current app UI/API reference because account products affect availability.
4. Put the resulting test credential in `HUBSPOT_ACCESS_TOKEN` in `.env`. Never commit it or paste it into logs.
5. In **Settings → Objects → Deals → Pipelines**, confirm at least one active pipeline and stage. Optionally copy their internal IDs to `HUBSPOT_PIPELINE_ID` and `HUBSPOT_INITIAL_STAGE_ID`. If omitted, the app reads pipelines and selects the first active pipeline and its lowest-display-order active stage.
6. No custom vehicle property is required. Vehicle interest is represented in the deal name and AI note; this avoids assuming a portal-specific custom schema.
7. Start the API and run `python3 scripts/verify_hubspot.py`.

The validation script creates uniquely named synthetic records and checks authentication, contact create/retrieve/update/search, deal create, association, stage update, note create and note retrieval. It does not print credentials and reports actual PASS/FAIL values. The synthetic records are retained for inspection; archive them manually in the test account after the demo.

Required API families use `2026-09`: CRM objects, pipelines and associations. See [API_DECISIONS.md](API_DECISIONS.md).

Troubleshooting:

- `401`: credential missing, expired, revoked or malformed.
- `403`: required scopes/record permissions are absent.
- `422` from this app: HubSpot rejected a configured property, pipeline, stage or portal validation rule.
- `429`: bounded retries were exhausted; wait for the rate-limit window.
- No pipeline: create/activate a deal pipeline and at least one stage in the test account.

