"""Resolve named bindings and record each occurrence against published values.

Copyright 2026 Dhruba Poudel
SPDX-License-Identifier: Apache-2.0
"""

from decimal import Decimal, localcontext
import re

from .sources import KEY_PATTERN


PLACEHOLDER = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)


def display_value(metric: dict) -> str:
    value = metric["value"]
    if metric["kind"] == "number":
        numeric = Decimal(value)
        if numeric == 0:
            numeric = Decimal(0)
        if metric.get("unit", "").lower() == "percent":
            with localcontext() as context:
                context.prec = 80
                percentage = format(numeric * 100, ",f")
            if "." in percentage:
                percentage = percentage.rstrip("0").rstrip(".")
            return percentage + "%"
        value = format(numeric, ",f")
    unit = metric.get("unit", "")
    if unit == "%":
        return value + "%"
    return value + (" " + unit if unit else "")


def render_template(template: dict, metrics: list[dict], published: dict | None = None,
                    source_warnings: list[str] | None = None) -> tuple[dict, list, list, list]:
    current = {item["key"]: item for item in metrics}
    previous = {item["key"]: item for item in (published or {}).get("metrics", [])}
    changes, errors = [], []
    warnings = list(source_warnings or [])
    referenced = set()

    def resolve(text: str, location: str, maximum: int) -> str:
        matches = list(PLACEHOLDER.finditer(text))
        remainder = PLACEHOLDER.sub("", text)
        if "{{" in remainder or "}}" in remainder:
            errors.append(f"{location}: incomplete placeholder. Use {{{{key}}}}.")
        if len(matches) > 100:
            errors.append(f"{location}: exceeds 100 linked values.")
        occurrence = 0

        def replacement(match):
            nonlocal occurrence
            occurrence += 1
            key = match.group(1).strip()
            item = current.get(key)
            old_item = previous.get(key)
            referenced.add(key)
            if not KEY_PATTERN.fullmatch(key):
                errors.append(f"{location}: invalid placeholder '{key}'.")
            elif item is None:
                errors.append(f"{location}: source key '{key}' is missing.")
            after = display_value(item) if item else None
            before = display_value(old_item) if old_item else None
            changes.append({"key": key, "label": (item or old_item or {}).get("label", key),
                            "location": f"{location} · occurrence {occurrence}",
                            "before": before, "after": after})
            return after if after is not None else f"[Missing: {key}]"

        result = PLACEHOLDER.sub(replacement, text)
        if len(result) > maximum:
            errors.append(f"{location}: rendered content exceeds {maximum} characters. Shorten the template or source value.")
        return result

    rendered = {"title": resolve(template["title"], "Report title", 120), "sections": [], "slides": []}
    for index, section in enumerate(template["sections"], start=1):
        rendered["sections"].append({
            "title": resolve(section["title"], f"Report section {index} title", 120),
            "body": resolve(section["body"], f"Report section {index} body", 4000),
        })
    for index, slide in enumerate(template["slides"], start=1):
        rendered["slides"].append({
            "title": resolve(slide["title"], f"Slide {index} title", 120),
            "body": resolve(slide["body"], f"Slide {index} body", 1200),
        })
    for key in sorted(referenced & current.keys() & previous.keys()):
        for field in ("kind", "unit", "period"):
            if current[key][field] != previous[key][field]:
                warnings.append(f"{key}: {field} changed from '{previous[key][field]}' to '{current[key][field]}'.")
    return rendered, changes, list(dict.fromkeys(warnings)), list(dict.fromkeys(errors))
