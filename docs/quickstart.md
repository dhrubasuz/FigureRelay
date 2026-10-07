# Quick start

Author: **Dhruba Poudel**.

After following the [README setup](../README.md#run-locally), open `http://127.0.0.1:8080`.

## Import a source

In **Sources**, choose **Load demo**, or choose **Import CSV or XLSX** with [sample-metrics.csv](sample-metrics.csv) to try the workflow without business data. The first row contains `key,label,value,kind,unit,period`. For Excel, use the same headers in a sheet named `Metrics`.

Keep the key stable when changing a label or a value. The sample's `revenue` key identifies the same metric across imports; the key is not a cell coordinate. More descriptive keys such as `revenue.total` are also valid. Duplicate keys are rejected. A key starts with a letter and contains only letters, digits, underscores, periods, colons, or hyphens.

Kinds are `number`, `text`, and `date`. Numbers must be finite decimals; dates use `YYYY-MM-DD`. A label is required. Units and periods can be blank when they do not apply. A CSV must be UTF-8. For numeric values, `percent` converts a fraction to a displayed percentage (`0.245` becomes `24.5%`), while `%` appends the symbol to an already scaled value (`24.5` becomes `24.5%`). Other units are appended to the value.

Formula cells in Excel must contain a saved cached result. Save and recalculate the workbook in its spreadsheet application before import. FigureRelay cannot verify cached-result freshness and does not run formulas; review formula warnings even when an import succeeds.

## Link occurrences

Open **Report** or **Slides**, edit the title or section/slide text, and choose **Save template**. Use the imported key inside double braces:

```text
Our revenue was {{revenue}}.
Operating costs were {{operating.costs}}.
The team had {{headcount}} members.
```

The prototype uses its built-in report and slide template model. It is not an add-in that automatically edits arbitrary existing Office files. Check the preview for every occurrence, including repeated appearances of a key. Correct unresolved keys before generating an approvable bundle.

## Review and approve

Choose **Generate preview** to create a candidate revision. With unsaved edits, **Save & preview** saves the template before generation. In **Review**, check its source values, templates, preview, and warnings. Choose **Approve & publish** for that specific revision only after checking it. This records a local approval; it does not upload or post to an external service. Actor names entered in the interface are descriptive labels and are not authenticated reviewer identities.

Prose edits appear in the candidate's rendered content. The linked-occurrence change list compares metric values and does not provide a prose diff against the earlier template. Read the complete report and slide previews when reviewing text changes. These browser previews do not verify final Office pagination or slide layout.

Generation freezes the candidate's file bytes. Approval refers to the exact revision you reviewed. **Export ZIP** returns its stored `report.docx`, `slides.pptx`, and `manifest.json`; it does not regenerate from whatever source is current at download time. **History** lists earlier generations, including approved bundles that remain exportable.

## Change a source

For a visible demonstration, choose **Stage sample v2** after loading demo data, or change `revenue` from `1250000` to `1325000` in a copy of the sample CSV, then import it and generate a new candidate. Inspect each linked occurrence before approving the new revision. An older approved bundle remains a snapshot of its own source and templates.

The manifest is useful provenance information. Local storage can be edited by its owner, so neither it nor the event history proves a tamper-proof chain of custody.
