"""Small, reproducible examples for the first-run walkthrough.

Copyright 2026 Dhruba Poudel
SPDX-License-Identifier: Apache-2.0
"""

DEMO_TEMPLATE = {
    "title": "{{period}} business review",
    "sections": [
        {"title": "Revenue and profitability", "body": "Revenue reached {{revenue}} with an operating margin of {{margin}}. The same revenue figure, {{revenue}}, is linked wherever it appears."},
        {"title": "Customer momentum", "body": "We served {{customers}} customers during {{period}}. This report and its slides share the same source keys."},
    ],
    "slides": [
        {"title": "{{period}} performance", "body": "Revenue: {{revenue}}\nOperating margin: {{margin}}\nCustomers: {{customers}}"},
        {"title": "One source, every occurrence", "body": "{{revenue}} appears here and in the report. Refresh the source, review every occurrence, and approve the exact preview before exporting."},
    ],
}

DEMO_V1 = b"key,label,value,kind,unit,period\nrevenue,Revenue,1250000,number,AUD,Q2 2026\nmargin,Operating margin,23.4,number,%,Q2 2026\ncustomers,Customers,1840,number,,Q2 2026\nperiod,Reporting period,Q2 2026,text,,Q2 2026\n"
DEMO_V2 = b"key,label,value,kind,unit,period\ncustomers,Customers,1960,number,,Q2 2026\nperiod,Reporting period,Q2 2026,text,,Q2 2026\nmargin,Operating margin,25.1,number,%,Q2 2026\nrevenue,Revenue,1420000,number,AUD,Q2 2026\n"
