# Demo

```bash
python3 -m pytest -q
python3 scripts/verify_hubspot.py
python3 scripts/verify_sheets.py
uvicorn app.main:app --reload --reload-dir app
```
Only proceed with the live CRM/Sheets portions if both verification scripts actually pass. Keep the HubSpot test account and test spreadsheet open; never use real customer data.

## Demo flow

1. Show `tests/fixtures/synthetic_leads.json` and state that all records are synthetic.
2. Send the README `POST /api/v1/leads/process` request. Point out the typed analysis, CRM IDs, unsent follow-up draft, Sheets flag, workflow ID and measured request time.
3. Open the HubSpot test contact. Show the matching deal and its association.
4. Open the CRM note and identify the summary, urgency, recommended action, draft and “human review required” wording.
5. Open the `Leads` worksheet and trace the row through the returned CRM IDs.
6. Repeat the identical API request. Show that the contact, active matching deal and sheet row are reused. Explain that a new note is intentional because each run is a distinct activity log.
7. Patch the deal stage using an ID previously retrieved from the test account, then refresh the deal.
8. Run `pytest -q` and show the current result. Explain why live tests are gated by `RUN_INTEGRATION_TESTS=true`.
9. Run `python3 scripts/benchmark.py --count 25` and explicitly identify it as a local mocked-integration benchmark. If a live benchmark has been run, show its separate artifact instead.