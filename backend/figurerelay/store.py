"""SQLite snapshots and transactions for the local review workflow.

Copyright 2026 Dhruba Poudel
SPDX-License-Identifier: Apache-2.0
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
import zipfile

from . import __version__
from .rendering import render_template
from .sources import ParsedSource


AUTHOR = "Dhruba Poudel"
DEFAULT_TEMPLATE = {
    "title": "Business report",
    "sections": [{"title": "Summary", "body": "Add a source and link a value with {{key}}."}],
    "slides": [{"title": "Business report", "body": "Add a source and link a value with {{key}}."}],
}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class WorkflowError(Exception):
    def __init__(self, status: int, detail: str):
        self.status, self.detail = status, detail
        super().__init__(detail)


class Store:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "figurerelay.sqlite3"
        with self.connect() as connection:
            connection.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, revision INTEGER NOT NULL,
                    source_version INTEGER NOT NULL, template TEXT NOT NULL,
                    published_id TEXT, candidate_id TEXT, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    project_id TEXT NOT NULL REFERENCES projects(id), version INTEGER NOT NULL,
                    filename TEXT NOT NULL, sha256 TEXT NOT NULL, original BLOB NOT NULL,
                    metrics TEXT NOT NULL, warnings TEXT NOT NULL, created_at TEXT NOT NULL,
                    PRIMARY KEY(project_id, version)
                );
                CREATE TABLE IF NOT EXISTS generations (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    revision INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    generation_id TEXT NOT NULL REFERENCES generations(id), name TEXT NOT NULL,
                    data BLOB NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(generation_id, name)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    event TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL, details TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS audit_by_project ON audit_events(project_id, created_at);
            """)

    @contextmanager
    def connect(self, write=False):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        if write:
            connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _project(connection, project_id):
        project = connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if project is None:
            raise WorkflowError(404, "Project was not found.")
        return project

    @staticmethod
    def _event(connection, project_id, event, details, actor="local"):
        connection.execute("INSERT INTO audit_events VALUES (?,?,?,?,?,?)",
                           (str(uuid4()), project_id, event, actor, timestamp(), encoded(details)))

    @staticmethod
    def _generation(connection, project_id, generation_id):
        row = connection.execute("SELECT * FROM generations WHERE id=? AND project_id=?",
                                 (generation_id, project_id)).fetchone()
        if row is None:
            raise WorkflowError(404, "Generation was not found in this project.")
        payload = json.loads(row["payload"])
        payload["status"] = row["status"]
        return payload

    def create_project(self, name, template=None):
        name = name.strip()
        if not name:
            raise WorkflowError(422, "Project name cannot be blank.")
        project_id, now = str(uuid4()), timestamp()
        with self.connect(write=True) as connection:
            connection.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?)",
                               (project_id, name, 0, 0, encoded(template or DEFAULT_TEMPLATE), None, None, now, now))
            self._event(connection, project_id, "project.created", {"name": name})
        return self.project(project_id)

    def list_projects(self):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT id,name,revision,source_version,updated_at FROM projects ORDER BY updated_at DESC,id")]

    def project(self, project_id):
        with self.connect() as connection:
            row = self._project(connection, project_id)
            source = connection.execute("SELECT metrics FROM sources WHERE project_id=? AND version=?",
                                        (project_id, row["source_version"])).fetchone()
            events = connection.execute("SELECT * FROM audit_events WHERE project_id=? ORDER BY created_at DESC,id DESC LIMIT 100",
                                        (project_id,)).fetchall()
            return {"id": row["id"], "name": row["name"], "revision": row["revision"],
                    "source_version": row["source_version"],
                    "metrics": json.loads(source["metrics"]) if source else [],
                    "template": json.loads(row["template"]),
                    "published": self._generation(connection, project_id, row["published_id"]) if row["published_id"] else None,
                    "candidate": self._generation(connection, project_id, row["candidate_id"]) if row["candidate_id"] else None,
                    "history": [{"id": item["id"], "event": item["event"], "actor": item["actor"],
                                 "created_at": item["created_at"], "details": json.loads(item["details"])} for item in events]}

    def update_template(self, project_id, template):
        with self.connect(write=True) as connection:
            row = self._project(connection, project_id)
            if json.loads(row["template"]) == template:
                return self.project(project_id)
            revision = row["revision"] + 1
            connection.execute("UPDATE projects SET template=?,revision=?,updated_at=? WHERE id=?",
                               (encoded(template), revision, timestamp(), project_id))
            self._event(connection, project_id, "template.updated", {"revision": revision})
        return self.project(project_id)

    def import_source(self, project_id, filename, data, parsed: ParsedSource):
        with self.connect(write=True) as connection:
            row = self._project(connection, project_id)
            version, revision, now = row["source_version"] + 1, row["revision"] + 1, timestamp()
            connection.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)",
                               (project_id, version, filename, parsed.sha256, data, encoded(parsed.metrics), encoded(parsed.warnings), now))
            connection.execute("UPDATE projects SET source_version=?,revision=?,updated_at=? WHERE id=?",
                               (version, revision, now, project_id))
            self._event(connection, project_id, "source.imported", {"revision": revision, "source_version": version,
                        "filename": filename, "sha256": parsed.sha256, "metric_count": len(parsed.metrics), "warnings": parsed.warnings})
        return self.project(project_id)

    def preview(self, project_id, expected_revision):
        # Holding a write transaction through rendering prevents an import from racing
        # between the snapshot read and the candidate being committed.
        with self.connect(write=True) as connection:
            project = self._project(connection, project_id)
            if project["revision"] != expected_revision:
                raise WorkflowError(409, "Project changed. Reload it and preview the current revision.")
            source = connection.execute("SELECT * FROM sources WHERE project_id=? AND version=?",
                                        (project_id, project["source_version"])).fetchone()
            metrics = json.loads(source["metrics"]) if source else []
            published = self._generation(connection, project_id, project["published_id"]) if project["published_id"] else None
            template = json.loads(project["template"])
            rendered, changes, warnings, errors = render_template(template, metrics, published,
                json.loads(source["warnings"]) if source else [])
            if source is None:
                errors.insert(0, "Import a source before generating a preview.")
            generation_id, now = str(uuid4()), timestamp()
            manifest = {"schema_version": 1, "application": "FigureRelay", "application_version": __version__,
                        "author": AUTHOR, "creator": AUTHOR, "last_modified_by": AUTHOR,
                        "generation_id": generation_id, "project_id": project_id, "project_name": project["name"],
                        "revision": project["revision"], "source_version": project["source_version"],
                        "source": {"filename": source["filename"], "sha256": source["sha256"]} if source else None,
                        "template_sha256": hashlib.sha256(encoded(template).encode("utf-8")).hexdigest(),
                        "created_at": now, "metrics": metrics, "bindings": changes,
                        "warnings": warnings, "errors": errors,
                        "review_policy": "Export requires approval of this exact revision.",
                        "audit_note": "Local review names are self-reported; this manifest is not a signed or tamperproof audit.",
                        "artifacts": []}
            artifacts = {}
            if not errors:
                from .exports import build_exports
                try:
                    artifacts = build_exports(rendered, manifest)
                except ValueError as exc:
                    errors.append(str(exc))
                    manifest["errors"] = errors
            if artifacts:
                if set(artifacts) != {"report.docx", "slides.pptx", "manifest.json"}:
                    raise RuntimeError("Exporter did not return the three required artifacts.")
                manifest = json.loads(artifacts["manifest.json"].decode("utf-8"))
                for item in manifest.get("artifacts", []):
                    content = artifacts.get(item["name"])
                    if content is None or item["sha256"] != hashlib.sha256(content).hexdigest() or item["size"] != len(content):
                        raise RuntimeError("Exporter artifact hash does not match the stored bytes.")
            payload = {"id": generation_id, "revision": project["revision"], "status": "pending", "created_at": now,
                       "metrics": metrics, "rendered": rendered, "changes": changes,
                       "warnings": warnings, "errors": errors, "manifest": manifest}
            connection.execute("INSERT INTO generations VALUES (?,?,?,?,?,?)",
                               (generation_id, project_id, project["revision"], "pending", now, encoded(payload)))
            for name, content in artifacts.items():
                connection.execute("INSERT INTO artifacts VALUES (?,?,?,?)",
                                   (generation_id, name, content, hashlib.sha256(content).hexdigest()))
            connection.execute("UPDATE projects SET candidate_id=?,updated_at=? WHERE id=?", (generation_id, now, project_id))
            self._event(connection, project_id, "generation.previewed", {"generation_id": generation_id,
                        "revision": project["revision"], "occurrences": len(changes), "warnings": warnings, "errors": errors})
            return payload

    def generation(self, project_id, generation_id):
        with self.connect() as connection:
            self._project(connection, project_id)
            return self._generation(connection, project_id, generation_id)

    def approve(self, project_id, generation_id, expected_revision, actor, acknowledge_warnings):
        actor = actor.strip()
        if not actor:
            raise WorkflowError(422, "Reviewer name cannot be blank.")
        with self.connect(write=True) as connection:
            project = self._project(connection, project_id)
            generation = self._generation(connection, project_id, generation_id)
            if expected_revision != project["revision"] or generation["revision"] != project["revision"]:
                raise WorkflowError(409, "This preview is stale. Generate and review a preview of the current revision.")
            if generation["status"] == "rejected":
                raise WorkflowError(409, "Rejected previews cannot be approved. Generate another preview.")
            if generation["errors"]:
                raise WorkflowError(422, "This preview has errors. Fix them before approving.")
            if generation["warnings"] and not acknowledge_warnings:
                raise WorkflowError(422, "Acknowledge all preview warnings before approving.")
            if generation["status"] == "approved":
                return generation
            count = connection.execute("SELECT count(*) FROM artifacts WHERE generation_id=?", (generation_id,)).fetchone()[0]
            if count != 3:
                raise WorkflowError(409, "Preview artifacts are incomplete. Generate another preview.")
            connection.execute("UPDATE generations SET status='approved' WHERE id=?", (generation_id,))
            connection.execute("UPDATE projects SET published_id=?,updated_at=? WHERE id=?", (generation_id, timestamp(), project_id))
            self._event(connection, project_id, "generation.approved", {"generation_id": generation_id,
                        "revision": generation["revision"], "acknowledge_warnings": acknowledge_warnings}, actor)
            generation["status"] = "approved"
            return generation

    def reject(self, project_id, generation_id, actor):
        actor = actor.strip()
        if not actor:
            raise WorkflowError(422, "Reviewer name cannot be blank.")
        with self.connect(write=True) as connection:
            self._project(connection, project_id)
            generation = self._generation(connection, project_id, generation_id)
            if generation["status"] == "approved":
                raise WorkflowError(409, "An approved generation is immutable and cannot be rejected.")
            if generation["status"] == "pending":
                connection.execute("UPDATE generations SET status='rejected' WHERE id=?", (generation_id,))
                self._event(connection, project_id, "generation.rejected", {"generation_id": generation_id,
                            "revision": generation["revision"]}, actor)
            generation["status"] = "rejected"
            return generation

    def export(self, project_id, generation_id):
        with self.connect(write=True) as connection:
            self._project(connection, project_id)
            generation = self._generation(connection, project_id, generation_id)
            if generation["status"] != "approved":
                raise WorkflowError(409, "Approve this exact preview before exporting.")
            rows = connection.execute("SELECT name,data,sha256 FROM artifacts WHERE generation_id=? ORDER BY name", (generation_id,)).fetchall()
            if len(rows) != 3 or {row["name"] for row in rows} != {"report.docx", "slides.pptx", "manifest.json"}:
                raise WorkflowError(409, "Stored artifacts are incomplete.")
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.comment = f"Prepared by {AUTHOR}".encode("utf-8")
                for row in rows:
                    content = bytes(row["data"])
                    if hashlib.sha256(content).hexdigest() != row["sha256"]:
                        raise WorkflowError(409, "A stored artifact failed its integrity check. Restore the local data from a trusted backup.")
                    entry = zipfile.ZipInfo(row["name"], date_time=(2026, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, content)
            self._event(connection, project_id, "generation.exported", {"generation_id": generation_id,
                        "revision": generation["revision"], "artifacts": [
                            {"name": row["name"], "sha256": row["sha256"], "size": len(row["data"])} for row in rows]})
            return output.getvalue()
