# Copyright 2026 Dhruba Poudel
# SPDX-License-Identifier: Apache-2.0

import pytest

from figurerelay.rendering import display_value, render_template


@pytest.mark.parametrize("value,unit,expected", [
    ("0.245", "percent", "24.5%"), ("0.2500", "percent", "25%"),
    ("23.4", "%", "23.4%"), ("1234.50", "USD", "1,234.50 USD"),
    ("-0.000", "", "0"), ("-0.000", "percent", "0%"),
    ("123456789012345678901234567890.1234567890", "percent", "12,345,678,901,234,567,890,123,456,789,012.3456789%"),
])
def test_explicit_formats_preserve_decimal_precision(value, unit, expected):
    assert display_value({"kind": "number", "value": value, "unit": unit}) == expected


def test_repeated_occurrences_and_literal_template_content_are_preserved():
    template = {"title": "{{x}} + {{x}}", "sections": [{"title": "Title", "body": "Value {{ x }} and {{x}}"}],
                "slides": [{"title": "Slide {{x}}", "body": "<script>alert(1)</script> {{x}}"}]}
    metric = {"key": "x", "label": "X", "kind": "text", "value": "<b>value</b>", "unit": "", "period": ""}
    rendered, changes, warnings, errors = render_template(template, [metric])
    assert len(changes) == 6
    assert len({c["location"] for c in changes}) == 6
    assert rendered["slides"][0]["body"] == "<script>alert(1)</script> <b>value</b>"
    assert not warnings and not errors


def test_unfinished_placeholder_and_rendered_length_are_errors():
    template = {"title": "{{x", "sections": [{"title": "Title", "body": "{{long}}"}],
                "slides": [{"title": "Slide", "body": "{{long}}"}]}
    metric = {"key": "long", "label": "Long", "kind": "text", "value": "v" * 1300, "unit": "", "period": ""}
    _, _, _, errors = render_template(template, [metric])
    assert any("incomplete placeholder" in e for e in errors)
    assert any("1200 characters" in e for e in errors)
