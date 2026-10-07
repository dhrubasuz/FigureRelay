# Copyright 2026 Dhruba Poudel
# SPDX-License-Identifier: Apache-2.0

from datetime import date
from io import BytesIO
import zipfile

import pytest
from openpyxl import Workbook

from figurerelay.sources import HEADERS, MAX_EXPANDED_BYTES, MAX_UPLOAD_BYTES, SourceError, parse_source


def workbook_bytes(rows, sheet="Metrics"):
    workbook = Workbook()
    workbook.properties.creator = "Dhruba Poudel"
    workbook.properties.lastModifiedBy = "Dhruba Poudel"
    worksheet = workbook.active
    worksheet.title = sheet
    worksheet.append(list(HEADERS))
    for row in rows:
        worksheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def cache_formula(data, cached="25.5"):
    output = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as old, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as new:
        for item in old.infolist():
            content = old.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                assert b"<f>10+15.5</f><v></v>" in content
                content = content.replace(b"<f>10+15.5</f><v></v>", f"<f>10+15.5</f><v>{cached}</v>".encode())
            new.writestr(item, content)
    return output.getvalue()


def test_csv_preserves_decimal_scale_blank_text_zero_and_stable_keys():
    first = b"key,label,value,kind,unit,period\nrevenue,Revenue,1234.50,number,AUD,Oct\nzero,Zero,0,number,,Oct\nempty,Blank,,text,,Oct\n"
    second = b"key,label,value,kind,unit,period\nempty,Blank,,text,,Oct\nrevenue,Revenue,1234.50,number,AUD,Oct\nzero,Zero,0,number,,Oct\n"
    a, b = parse_source("a.csv", first), parse_source("b.csv", second)
    assert {m["key"]: m for m in a.metrics} == {m["key"]: m for m in b.metrics}
    assert [m["value"] for m in a.metrics] == ["1234.50", "0", ""]
    assert a.sha256 != b.sha256


@pytest.mark.parametrize("row,message", [
    ("a,A,NaN,number,,", "finite"),
    ("a,A,Infinity,number,,", "finite"),
    ("a,A,1e1000000,number,,", "finite"),
    ("a,A,,number,,", "required"),
    ("a,A,1,money,,", "kind"),
    ("a,A,2026-02-30,date,,", "YYYY-MM-DD"),
    ("1a,A,1,number,,", "key"),
    ("a,,1,number,,", "label"),
])
def test_bad_metric_is_rejected(row, message):
    with pytest.raises(SourceError, match=message):
        parse_source("bad.csv", ("key,label,value,kind,unit,period\n" + row + "\n").encode())


def test_duplicate_keys_and_schema_do_not_import():
    with pytest.raises(SourceError, match="duplicate key"):
        parse_source("bad.csv", b"key,label,value,kind,unit,period\na,A,1,number,,\na,B,2,number,,\n")
    with pytest.raises(SourceError, match="exactly"):
        parse_source("bad.csv", b"key,label,value,kind,unit,period,extra\na,A,1,number,,,x\n")


def test_xlsx_literal_values_and_dates():
    data = workbook_bytes([["revenue", "Revenue", 1200.5, "number", "AUD", "October"],
                           ["date", "As of", date(2026, 10, 7), "date", "", ""]])
    parsed = parse_source("source.xlsx", data)
    assert parsed.metrics[0]["value"] == "1200.5"
    assert parsed.metrics[1]["value"] == "2026-10-07"
    assert parsed.warnings == []


def test_formula_without_cache_blocks_import_and_cached_formula_warns():
    data = workbook_bytes([["margin", "Margin", "=10+15.5", "number", "%", ""]])
    with pytest.raises(SourceError, match="no stored result"):
        parse_source("source.xlsx", data)
    parsed = parse_source("source.xlsx", cache_formula(data))
    assert parsed.metrics[0]["value"] == "25.5"
    assert len(parsed.warnings) == 1
    assert "freshness cannot be verified" in parsed.warnings[0]


def test_excel_errors_formula_identity_and_wrong_sheet_block_import():
    for row, message in [(["a", "A", "#DIV/0!", "number", "", ""], "Excel error"),
                         (["=A2", "A", 1, "number", "", ""], "only in the value")]:
        with pytest.raises(SourceError, match=message):
            parse_source("source.xlsx", workbook_bytes([row]))
    with pytest.raises(SourceError, match="named Metrics"):
        parse_source("source.xlsx", workbook_bytes([["a", "A", 1, "number", "", ""]], "Other"))


def test_file_types_upload_size_and_expanded_zip_limit():
    with pytest.raises(SourceError, match=".csv or .xlsx"):
        parse_source("source.xlsm", b"fake")
    with pytest.raises(SourceError, match="5 MB"):
        parse_source("source.csv", b"x" * (MAX_UPLOAD_BYTES + 1))
    with pytest.raises(SourceError, match="readable XLSX"):
        parse_source("source.xlsx", b"not a zip")
    bomb = BytesIO()
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "placeholder")
        archive.writestr("xl/workbook.xml", "x" * (MAX_EXPANDED_BYTES + 1))
    with pytest.raises(SourceError, match="expanded content"):
        parse_source("source.xlsx", bomb.getvalue())
