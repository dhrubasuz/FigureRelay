# Demonstrate the review and export workflow

Author: **Dhruba Poudel**.

This demonstration answers one practical question: after a source figure changes, can a reviewer see each affected occurrence while the previously approved Office files remain unchanged?

Use the built-in synthetic data only. The example is a local prototype demonstration, not an organisational approval or financial-assurance system.

## Walk through the interface

Follow the [local setup](../README.md#run-locally), then open `http://127.0.0.1:8080`.

| Step | Action | What to inspect |
| --- | --- | --- |
| 1 | In **Sources**, choose **Load demo**. | The named metrics include revenue of `1,250,000 AUD`. |
| 2 | Open **Report** and **Slides**. | The same `revenue` key appears twice in the report and twice across the slides. |
| 3 | Choose **Generate preview** and open **Review**. | Review all four occurrences, the complete prose, source, revision and warnings. |
| 4 | Approve that candidate, then choose **Export ZIP**. | Save the approved v1 bundle with `report.docx`, `slides.pptx` and `manifest.json`. |
| 5 | Choose **Stage sample v2**, then generate another preview. | All four revenue occurrences change to `1,420,000 AUD`; source row order does not determine link identity. |
| 6 | Review and approve v2. Download the older approved bundle from **History** as well. | The older files still contain v1 values. Opening a newer source does not silently rewrite an earlier approval. |

Open the exported Word document and PowerPoint slides in an Office application before sharing them. Browser previews are not a final layout check. Keep both versions when demonstrating the revision boundary.

## Reproduce the artifact checks

After installing the development dependencies and editable backend package, run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/verify_demo.py --output .figurerelay/demo-verification
```

On macOS or Linux, use `.venv/bin/python` instead. Choose a new or empty output directory; the command refuses to replace existing files. It uses a temporary database and does not read or modify the normal application data directory.

The command uses the real application API through FastAPI's in-process test client. It does not require a running web server and does not exercise the browser interface. It checks:

- Unapproved exports are blocked.
- Both revisions contain the expected figure in all four Office occurrences.
- Word and PowerPoint identify the reviewed generation and set Author and Last Modified By to Dhruba Poudel.
- The manifest revision, artifact sizes and SHA-256 checksums match the actual exported bytes.
- The old approved ZIP stays byte-identical after the second approval and after application restart.

The output directory contains two ZIP bundles, their extracted Office files/manifests, and `verification.json` with the checks actually completed. The generated evidence includes no employer data, credentials or normal application database.

## What this demonstrates

The project connects CSV/XLSX validation, stable data keys, a React/TypeScript review interface, a Python/FastAPI service, SQLite revision state and attributed Office exports. The important design boundary is the frozen candidate: approval refers to reviewed bytes, not to data that might change before download.

The local actor name is a descriptive label. This demonstration does not establish authenticated independent approvals, immutable audit storage, Excel formula recalculation, arbitrary existing Office layout preservation or regulatory suitability. See [architecture](architecture.md) and [security](../SECURITY.md) for those boundaries.
