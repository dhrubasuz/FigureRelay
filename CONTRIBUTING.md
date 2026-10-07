# Contributing to FigureRelay

Project maintainer: **Dhruba Poudel**.

Start with a small, clearly described change. A bug report, documentation fix, accessibility improvement, or test of a source-to-export boundary is valuable.

## Before opening a change

- Check existing issues and explain the problem a change will solve.
- Discuss changes to the metric schema, revision semantics, exports, or public API before implementing them.
- Use synthetic data. Do not submit confidential reports, credentials, or customer files.
- For bugs, include the version or commit, operating system, reproduction steps, expected result, actual result, and a minimal safe example.

Security vulnerabilities should follow [SECURITY.md](SECURITY.md), rather than a public issue containing exploit details or sensitive files.

## Development and review

Follow [docs/development.md](docs/development.md). Keep a pull request focused, explain its behaviour, and include checks that exercise the changed behaviour. State which checks you actually ran; do not claim a passing check from its presence in a workflow.

Changes affecting exports must preserve the approved-revision boundary: exporting an approved bundle returns that candidate's stored bytes, rather than regenerating from the latest source. Imports must preserve key identity and reject ambiguous or invalid data. Generated Office files must preserve the requested author metadata, **Dhruba Poudel**.

The maintainer reviews changes for correctness, scope, maintainability, security, and documentation. A contribution may be declined or deferred when it falls outside the current prototype's scope. New contributors are welcome to ask for help in a public issue using safe examples.

## Licence and Developer Certificate of Origin

Contributions intended for inclusion are made under Apache-2.0. Contributors retain ownership of their contributions; this project does not require copyright assignment or a separate Contributor Licence Agreement.

Each contributed commit must include a `Signed-off-by` trailer certifying [Developer Certificate of Origin 1.1](DCO):

```text
Signed-off-by: Your Name <your-contribution-email>
```

This is a certification of your right to submit the work, not a cryptographic signature. Read the DCO before signing. Your contribution and its sign-off become part of the public record.

Submit only work you are authorised to license. Obtain the necessary authorisation for employer-owned work. Identify third-party code, assets, and their licences, and preserve applicable notices. You are responsible for understanding and validating tool-assisted contributions. Do not submit unexplained generated code or material whose origin or licence you cannot establish.

If a sign-off is missing, add it before merge. Maintainers should preserve sign-offs when rebasing or squashing, and must not invent a contributor's certification.

## Community expectations

Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Be respectful, provide useful reproduction details, and discuss technical disagreements in terms of evidence and project goals.
