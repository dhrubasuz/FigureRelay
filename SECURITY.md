# Security policy

Maintainer: **Dhruba Poudel**.

## Supported versions

FigureRelay 0.1 is a local prototype, not a hardened hosted service. While it is unreleased, security fixes target the current development branch. Once a stable release exists, this project will support the latest stable release unless a release note explicitly states otherwise.

## Reporting a vulnerability

GitHub private vulnerability reporting is enabled for this repository. Sign in to GitHub, open [FigureRelay's security advisories](https://github.com/dhrubasuz/FigureRelay/security/advisories), and choose **Report a vulnerability** to send a private report.

The available controls depend on your GitHub account and repository access; owners may see advisory-management controls instead of the reporter entry point. If the report control is unavailable, check that you are signed in with an account that can access the repository. Do not put confidential files, credentials, personal information, or exploitable vulnerability details in a public issue. If you already have an established private contact with the maintainer, you may use that channel.

A useful report includes the affected version, platform, impact, reproducible steps, and a minimal synthetic example. Coordinate disclosure with the maintainer so a fix can be prepared. Response and repair times depend on maintainer availability.

## Deployment and trust boundary

- The default server binds to `127.0.0.1:8080`. Do not expose this prototype to a network as a multi-user service without adding authentication, authorisation, isolation, and deployment review.
- Entered actor names are unverified labels. An approval in this version does not establish an independently authenticated reviewer.
- The SQLite database and stored bundles belong to the local user account. Someone with write access to that storage can alter or remove them. The event history and manifest are not tamper-proof or regulatory audit evidence.
- Treat spreadsheet content and document templates as untrusted inputs. The importer enforces upload, archive expansion, entry-count, and metric-count limits; these are safeguards, not a claim that every malicious file is harmless.
- Excel cached formula results can be stale. FigureRelay does not calculate formulas or certify financial correctness.
- Imports, generated artifacts, and audit records can contain business information. Keep the data directory and exported ZIPs in a location appropriate for that information. Do not commit them to GitHub.

## Maintainer release checks

Review dependency updates, input parsing and export boundaries, browser rendering of imported content, local request handling, and whether a change broadens file or network access. Check that GitHub private vulnerability reporting remains enabled and that this policy matches the current route. Confirm that published source, samples, screenshots, logs, and history contain no confidential material.
