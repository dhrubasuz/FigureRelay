# Synthetic reporting examples

Created by Dhruba Poudel. These values describe a fictional organization.

Import `metrics-v1.csv`, link the `revenue`, `margin`, and `customers` metrics,
and publish a snapshot. Import `metrics-v2.csv` into the same project to review
the changes. Rows intentionally move in the second file: metric identities
follow `key`, rather than the old row number.

The `percent` unit treats `0.245` as 24.5%, and `USD` is a currency label; it does
not request a currency conversion. CSV examples contain literal values.

Copyright 2026 Dhruba Poudel. SPDX-License-Identifier: Apache-2.0.
