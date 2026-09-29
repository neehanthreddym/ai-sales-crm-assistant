# Google Sheets setup

1. Create a dedicated Google Cloud project for this POC.
2. Enable **Google Sheets API**. Drive API is not required by this application.
3. Create a service account for local testing, or configure Application Default Credentials/workload identity in the runtime.
4. If using a local service account, create a JSON key, store it outside the repository, and set `GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/key.json`.
5. Create a spreadsheet manually and add a worksheet named `Leads` (or set `GOOGLE_SHEETS_WORKSHEET`).
6. Share that spreadsheet with the service-account email as **Editor**. This grants access to that file without a Drive-wide OAuth scope.
7. Copy the ID between `/d/` and `/edit` in the spreadsheet URL to `GOOGLE_SHEETS_SPREADSHEET_ID`.
8. Run `python3 scripts/verify_sheets.py`.

The client requests only `https://www.googleapis.com/auth/spreadsheets`. It reads columns A:M, validates/creates the documented header, appends a new synthetic row, locates it, updates it and verifies only one matching contact-ID row exists. The validation row remains for inspection and can be deleted manually.

Do not commit service-account JSON. Rotate a key immediately if it is exposed. Prefer keyless workload identity for a hosted implementation.

