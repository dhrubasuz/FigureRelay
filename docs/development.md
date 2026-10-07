# Development

Author: **Dhruba Poudel**.

Use Python 3.11+, Node.js 24, and pnpm 11.19.0. The CI workflow uses Python 3.13 and Node.js 24. Begin with the dependency installation commands in [README.md](../README.md#run-locally).

## Local interface development

Start the installed backend with `python -m figurerelay` from the repository root, using your virtual environment's Python. It binds to `127.0.0.1:8080`.

Run `pnpm --dir frontend dev` in another terminal to use Vite's development server. For the interface served directly by FastAPI, rebuild with `pnpm --dir frontend build`.

Set `FIGURERELAY_DATA_DIR` when you want a separate scratch database and generated bundles. Do not use real reporting data in screenshots, tests, or committed fixtures.

## Checks

Run these from the repository root with the virtual environment active, or replace `python` with its explicit path:

```sh
python -m pytest backend/tests
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend build
```

These are commands to perform checks, not a claim that they have already passed. A pull request should report the checks actually run and any material limitations.

Useful behavioural checks cover invalid/duplicate metrics, formula-cache handling, unresolved links, repeated occurrences, source changes after candidate generation, exact-revision approval, and export of the original stored bytes. Tests of Office exports should inspect document contents and author metadata, rather than only checking that a ZIP exists.

## Dependencies and licences

Keep `frontend/pnpm-lock.yaml` current and use `pnpm --dir frontend install --frozen-lockfile` for reproducible frontend installs. Backend requirements and project metadata define the Python dependencies. When adding or upgrading a dependency, inspect its licence, provenance, and notices and update [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Do not infer a component's licence from its repository description alone.

`backend/requirements-dev.txt` applies `backend/requirements-lock.txt` as constraints before installing runtime and test requirements. These pins record the versions tested in the Python 3.12 verification environment. They include runtime and development dependencies; they are not a complete platform-independent lock with artifact hashes. Python version, operating system, package build, and package-index availability can still affect an installation. Refresh the constraints and rerun the relevant checks when dependencies change.

## CI

[.github/workflows/ci.yml](../.github/workflows/ci.yml) runs backend tests and frontend tests/type/build checks. It has a read-only repository token, does not publish artifacts or deploy, and avoids privileged pull-request triggers. Actions are pinned to specific commits; update their pins intentionally.

The existence of a workflow does not mean it has run. Consult the actual CI result for the revision under review.
