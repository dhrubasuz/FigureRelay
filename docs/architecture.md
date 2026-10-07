# Architecture and revision boundaries

Author: **Dhruba Poudel**.

FigureRelay 0.1 consists of a React/TypeScript interface built with Vite and a Python FastAPI service. The local service runs at `127.0.0.1:8080`, serves the built interface, and persists application state in SQLite.

## Data flow

```text
CSV / XLSX Metrics sheet
          |
          v
Validated named metrics -------> Report and slide templates
          |                                  |
          +---------- current source --------+
                             |
                             v
                 Candidate generation
                   frozen file bytes
                  + revision + manifest
                             |
                             v
                  Exact-revision approval
                             |
                             v
                  Stored approved ZIP
```

## Metric identity and parsing

Keys are the link identity. Labels, values, units, and periods describe a metric; renaming the key changes its identity. Input validation rejects duplicates and invalid types rather than selecting an arbitrary row. The importer bounds compressed size, archive expansion, ZIP-entry count, and number of metrics.

For Excel, the parser reads the `Metrics` worksheet. It does not calculate formulas. A formula requires a stored cached result; imports warn that freshness is unverified. A missing cache blocks the import. Code that changes parsing must keep this limitation explicit.

## Linking and rendering

The prototype's built-in template model uses `{{key}}` placeholders. The interface exposes linked occurrences so the same figure can be reviewed wherever it appears. Rendering should distinguish unresolved references from an intentional blank value; it must not quietly substitute a different metric.

The generated candidate contains the current template prose. The occurrence change list compares linked metric values; it does not produce a prose diff of additions, deletions, or rewritten text. Reviewers must read the rendered report and slides to assess those changes. The browser preview does not certify the final Office layout.

Output generation creates `report.docx`, `slides.pptx`, and `manifest.json`. Generated Office files set Author/Creator and Last Modified By fields to Dhruba Poudel. The manifest records revision/provenance information; it is not a cryptographic certification or regulatory attestation.

## Generation, approval, and export

Generation is the snapshot boundary. A candidate has the source/template state used for generation and stored artifact bytes. Approval names the exact candidate revision. Export returns the stored bytes for an approved revision, including after a later source import or candidate generation. A change must never cause an old approved bundle to silently contain newer values.

Local actor names help describe actions, but are not authenticated identities. The SQLite state and event history are locally writable and not tamper-proof. Multi-user roles, independent approvals, hosted access, and immutable audit storage require separate design and implementation.

## Storage and operation

`FIGURERELAY_DATA_DIR` can select a local data directory. Use a path appropriate for the imported information, and keep it outside source control. The process owner has access to that storage and its exported artifacts. The default loopback binding is part of the prototype's operating model.

The repository includes a Dockerfile and Compose configuration, but their container build/run path has not been verified in this session. The prototype demonstration uses the local Python/Node setup.

## Extension priorities

Future changes may add source connectors, richer template models, document formats, authenticated collaboration, and stronger provenance. Each must preserve stable metric identity, clear source/template revision relationships, and the frozen approval/export boundary. Discussion belongs in an issue before implementation of a public-contract change.
