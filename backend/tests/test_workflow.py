# Copyright 2026 Dhruba Poudel
# SPDX-License-Identifier: Apache-2.0

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
from io import BytesIO
import json
import sqlite3
import threading
import zipfile

from fastapi.testclient import TestClient
import pytest

from figurerelay.app import create_app
from figurerelay.demo import DEMO_V1, DEMO_V2
from figurerelay.sources import MAX_UPLOAD_BYTES, parse_source
from figurerelay.store import Store, WorkflowError
from test_sources import cache_formula, workbook_bytes


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path), base_url="http://127.0.0.1:8080") as application:
        yield application


def preview(client, project):
    response = client.post(f"/api/projects/{project['id']}/preview", json={"expected_revision": project["revision"]})
    assert response.status_code == 201, response.text
    return response.json()


def approve(client, project, generation, acknowledge=True):
    return client.post(f"/api/projects/{project['id']}/generations/{generation['id']}/approve", json={
        "expected_revision": project["revision"], "actor": "Dhruba Poudel", "acknowledge_warnings": acknowledge})


def export_files(client, project, generation):
    response = client.get(f"/api/projects/{project['id']}/generations/{generation['id']}/export")
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_end_to_end_occurrences_approval_frozen_export_and_restart(client, tmp_path):
    project = client.post("/api/demo").json()
    candidate = preview(client, project)
    assert candidate["status"] == "pending"
    assert candidate["errors"] == []
    revenue = [change for change in candidate["changes"] if change["key"] == "revenue"]
    assert len(revenue) == 4  # two report occurrences and two slides
    assert len({change["location"] for change in revenue}) == 4
    assert all(change["before"] is None and change["after"] == "1,250,000 AUD" for change in revenue)
    blocked = client.get(f"/api/projects/{project['id']}/generations/{candidate['id']}/export")
    assert blocked.status_code == 409
    assert approve(client, project, candidate).status_code == 200
    files = export_files(client, project, candidate)
    assert set(files) == {"report.docx", "slides.pptx", "manifest.json"}
    manifest = json.loads(files["manifest.json"])
    for artifact in manifest["artifacts"]:
        assert hashlib.sha256(files[artifact["name"]]).hexdigest() == artifact["sha256"]
        assert len(files[artifact["name"]]) == artifact["size"]
    current = client.post(f"/api/projects/{project['id']}/demo-revision").json()
    assert current["revision"] == project["revision"] + 1
    next_candidate = preview(client, current)
    changes = [change for change in next_candidate["changes"] if change["key"] == "revenue"]
    assert all(change["before"] == "1,250,000 AUD" and change["after"] == "1,420,000 AUD" for change in changes)
    assert export_files(client, project, candidate) == files
    with TestClient(create_app(tmp_path), base_url="http://127.0.0.1:8080") as restarted:
        saved = restarted.get(f"/api/projects/{project['id']}").json()
        assert saved["published"]["id"] == candidate["id"]
        assert saved["candidate"]["id"] == next_candidate["id"]
        assert any(e["event"] == "generation.approved" and e["actor"] == "Dhruba Poudel" for e in saved["history"])
        exported = [e for e in saved["history"] if e["event"] == "generation.exported"]
        assert exported and exported[0]["details"]["generation_id"] == candidate["id"]
        assert all(len(item["sha256"]) == 64 for item in exported[0]["details"]["artifacts"])
        assert export_files(restarted, project, candidate) == files


@pytest.mark.parametrize("change", ["source", "template"])
def test_edits_block_stale_preview_approval(client, change):
    project = client.post("/api/demo").json()
    candidate = preview(client, project)
    if change == "source":
        updated = client.post(f"/api/projects/{project['id']}/demo-revision").json()
    else:
        template = deepcopy(project["template"])
        template["title"] = "New title"
        updated = client.put(f"/api/projects/{project['id']}/template", json=template).json()
    assert updated["candidate"]["id"] == candidate["id"]
    assert approve(client, project, candidate).status_code == 409
    assert approve(client, updated, candidate).status_code == 409
    assert client.post(f"/api/projects/{project['id']}/preview", json={"expected_revision": project["revision"]}).status_code == 409


def test_missing_key_never_uses_published_value(client):
    project = client.post("/api/demo").json()
    old = preview(client, project)
    assert approve(client, project, old).status_code == 200
    data = b"key,label,value,kind,unit,period\nperiod,Reporting period,Q2 2026,text,,Q2 2026\n"
    current = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("missing.csv", data)}).json()
    candidate = preview(client, current)
    assert candidate["errors"]
    missing = [change for change in candidate["changes"] if change["key"] == "revenue"]
    assert all(change["before"] == "1,250,000 AUD" and change["after"] is None for change in missing)
    assert "1,250,000 AUD" not in candidate["rendered"]["sections"][0]["body"]
    assert "[Missing: revenue]" in candidate["rendered"]["sections"][0]["body"]
    assert approve(client, current, candidate).status_code == 422
    assert client.get(f"/api/projects/{project['id']}/generations/{candidate['id']}/export").status_code == 409


def test_formula_warning_requires_explicit_acknowledgment(client):
    project = client.post("/api/projects", json={"name": "Formula review"}).json()
    template = {"title": "Formula review", "sections": [{"title": "Summary", "body": "Margin {{margin}}"}],
                "slides": [{"title": "Margin", "body": "{{margin}}"}]}
    client.put(f"/api/projects/{project['id']}/template", json=template)
    data = cache_formula(workbook_bytes([["margin", "Margin", "=10+15.5", "number", "%", ""]]))
    response = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("cached.xlsx", data)})
    assert response.status_code == 200
    current = response.json()
    candidate = preview(client, current)
    assert candidate["warnings"]
    assert approve(client, current, candidate, acknowledge=False).status_code == 422
    assert approve(client, current, candidate, acknowledge=True).status_code == 200


def test_bad_import_is_atomic_and_rejection_cannot_reverse_approval(client):
    project = client.post("/api/demo").json()
    response = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("bad.csv", b"bad data")})
    assert response.status_code == 422
    assert client.get(f"/api/projects/{project['id']}").json() == project
    candidate = preview(client, project)
    url = f"/api/projects/{project['id']}/generations/{candidate['id']}"
    assert client.post(url + "/reject", json={"actor": "Dhruba Poudel"}).json()["status"] == "rejected"
    assert approve(client, project, candidate).status_code == 409
    approved = preview(client, project)
    assert approve(client, project, approved).status_code == 200
    assert client.post(f"/api/projects/{project['id']}/generations/{approved['id']}/reject", json={"actor": "Dhruba Poudel"}).status_code == 409


def test_unit_and_period_changes_are_warnings_requiring_acknowledgment(client):
    project = client.post("/api/demo").json()
    old = preview(client, project)
    assert approve(client, project, old).status_code == 200
    data = DEMO_V2.replace(b"Q2 2026", b"Q3 2026").replace(b",AUD,", b",USD,")
    current = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("changed.csv", data)}).json()
    candidate = preview(client, current)
    assert any("unit changed" in w for w in candidate["warnings"])
    assert any("period changed" in w for w in candidate["warnings"])
    assert approve(client, current, candidate, acknowledge=False).status_code == 422
    assert approve(client, current, candidate).status_code == 200


def test_chunked_multipart_input_is_bounded_before_unlimited_spooling(client):
    project = client.post("/api/demo").json()

    def body():
        yield b'--testboundary\r\nContent-Disposition: form-data; name="file"; filename="big.csv"\r\nContent-Type: text/csv\r\n\r\n'
        for _ in range(84):
            yield b"x" * 65536
        yield b"\r\n--testboundary--\r\n"

    response = client.post(f"/api/projects/{project['id']}/sources", content=body(), headers={
        "Content-Type": "multipart/form-data; boundary=testboundary"})
    assert response.status_code == 413


def test_loopback_browser_protection_file_limits_and_foreign_project(client):
    assert client.get("/api/health").json()["author"] == "Dhruba Poudel"
    assert client.post("/api/demo", headers={"Origin": "https://attacker.example"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 403
    assert client.post("/api/demo", headers={"Origin": "null"}).status_code == 403
    assert client.get("/api/health", headers={"Origin": "http://localhost:5173"}).status_code == 200
    project = client.post("/api/demo").json()
    assert client.post(f"/api/projects/{project['id']}/sources", files={"file": ("huge.csv", b"x" * (MAX_UPLOAD_BYTES + 1))}).status_code == 413
    assert client.post(f"/api/projects/{project['id']}/sources", files={"file": ("no.xlsm", b"x")}).status_code == 422
    candidate = preview(client, project)
    other = client.post("/api/demo").json()
    assert client.get(f"/api/projects/{other['id']}/generations/{candidate['id']}").status_code == 404


def test_rendered_layout_errors_are_reviewable_not_server_errors(client):
    project = client.post("/api/demo").json()
    template = deepcopy(project["template"])
    template["slides"][0]["body"] = "line\n" * 80
    current = client.put(f"/api/projects/{project['id']}/template", json=template).json()
    candidate = preview(client, current)
    assert any("layout" in error for error in candidate["errors"])
    assert approve(client, current, candidate).status_code == 422


def test_integrity_check_detects_altered_stored_artifact(client):
    project = client.post("/api/demo").json()
    candidate = preview(client, project)
    assert approve(client, project, candidate).status_code == 200
    with sqlite3.connect(client.app.state.store.path) as connection:
        connection.execute("UPDATE artifacts SET data=? WHERE generation_id=? AND name='report.docx'", (b"altered", candidate["id"]))
    response = client.get(f"/api/projects/{project['id']}/generations/{candidate['id']}/export")
    assert response.status_code == 409
    assert "integrity" in response.json()["detail"]


def test_atomic_approval_sees_committed_source_revision(tmp_path):
    store = Store(tmp_path)
    project = store.create_project("Race", {"title": "Review", "sections": [{"title": "Revenue", "body": "{{revenue}}"}],
                                            "slides": [{"title": "Revenue", "body": "{{revenue}}"}]})
    project = store.import_source(project["id"], "v1.csv", DEMO_V1, parse_source("v1.csv", DEMO_V1))
    candidate = store.preview(project["id"], project["revision"])
    started = threading.Event()

    def approve_after_lock():
        started.set()
        try:
            store.approve(project["id"], candidate["id"], project["revision"], "Dhruba Poudel", True)
        except WorkflowError as exc:
            return exc.status
        return 200

    with ThreadPoolExecutor(max_workers=1) as pool:
        with store.connect(write=True) as connection:
            result = pool.submit(approve_after_lock)
            assert started.wait(2)
            connection.execute("UPDATE projects SET revision=revision+1 WHERE id=?", (project["id"],))
        assert result.result(timeout=5) == 409
    assert store.generation(project["id"], candidate["id"])["status"] == "pending"
