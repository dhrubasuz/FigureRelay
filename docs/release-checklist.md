# Release checklist

Author: **Dhruba Poudel**.

The current project is a local prototype. This checklist describes work to complete for a release; it is not a record that the work has already been done.

1. Review the intended commit, dependency lockfile, backend requirements, licence texts, and third-party notices.
2. Run backend tests and frontend type checks and builds. Review actual CI results for that commit.
3. Start from a clean installation and complete the sample import, repeated-placeholder preview, candidate generation, exact-revision approval, and ZIP download.
4. Check the exported Word and PowerPoint content, author metadata, manifest, and unchanged bytes of an older approved generation after a new import.
5. Check error handling for malformed files, duplicate keys, missing formula caches, and unresolved placeholders using synthetic data.
6. Before opening a public community, configure a verified private route for vulnerability and conduct reports and update SECURITY.md and CODE_OF_CONDUCT.md. Do not claim that GitHub's private reporting button is active until it has been enabled and checked.
7. Confirm that no real reports, credentials, local databases, generated publication bundles, or machine-specific files are included.
8. Update the changelog, version fields, supported-version statement, and installation instructions to match the release.
9. Publish release notes with verified behaviour and limitations. Include a safe example and the exact revision. Use screenshots or demonstrations only from synthetic data.
10. Review issues and feedback after release. Treat stars as a discovery signal; measure successful installs, completed workflows, and repeat usage to learn whether the project helps people.
