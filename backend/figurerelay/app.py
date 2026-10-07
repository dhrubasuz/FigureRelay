"""Loopback-first API and optional built frontend for the local application.

Copyright 2026 Dhruba Poudel
SPDX-License-Identifier: Apache-2.0
"""

import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.staticfiles import StaticFiles

from . import __version__
from .demo import DEMO_TEMPLATE, DEMO_V1, DEMO_V2
from .models import ApproveRequest, PreviewRequest, ProjectCreate, RejectRequest, Template
from .sources import MAX_UPLOAD_BYTES, SourceError, parse_source
from .store import AUTHOR, Store, WorkflowError


MAX_BODY_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEV_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173", "http://[::1]:5173"}


class RequestLimit:
    """Bound multipart input before the parser can spool an unbounded upload."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        try:
            oversized = length is not None and int(length) > MAX_BODY_BYTES
        except ValueError:
            response = JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)
            return await response(scope, receive, send)
        if oversized:
            response = JSONResponse({"detail": "Request exceeds the 5 MB source upload limit."}, status_code=413)
            return await response(scope, receive, send)
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > MAX_BODY_BYTES:
                raise HTTPException(413, "Request exceeds the 5 MB source upload limit.")
            return message

        return await self.app(scope, limited_receive, send)


def create_app(data_dir=None) -> FastAPI:
    project_root = Path(__file__).resolve().parents[2]
    directory = data_dir or os.environ.get("FIGURERELAY_DATA_DIR") or project_root / ".figurerelay"
    store = Store(directory)
    app = FastAPI(title="FigureRelay", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.store = store
    app.add_middleware(RequestLimit)
    app.add_middleware(CORSMiddleware, allow_origins=sorted(DEV_ORIGINS),
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Content-Type"], allow_credentials=False)

    @app.middleware("http")
    async def local_origin_only(request: Request, call_next):
        host = request.headers.get("host", "")
        try:
            host_url = urlsplit("http://" + host)
            if host_url.hostname not in LOOPBACK_HOSTS or host_url.username or host_url.password:
                return JSONResponse({"detail": "FigureRelay accepts loopback hostnames only."}, status_code=403)
            origin = request.headers.get("origin")
            if origin:
                origin_url = urlsplit(origin)
                same_origin = (origin_url.scheme in {"http", "https"} and origin_url.netloc == host
                               and origin_url.path == "" and not origin_url.query and not origin_url.fragment)
                if origin_url.hostname not in LOOPBACK_HOSTS or not (same_origin or origin in DEV_ORIGINS):
                    return JSONResponse({"detail": "Requests from this browser origin are not allowed."}, status_code=403)
        except ValueError:
            return JSONResponse({"detail": "Invalid local host or origin."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(WorkflowError)
    async def workflow_error(request, exc):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status)

    @app.exception_handler(SourceError)
    async def source_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "author": AUTHOR, "mode": "local"}

    @app.get("/api/projects")
    def projects():
        return store.list_projects()

    @app.post("/api/projects", status_code=201)
    def new_project(body: ProjectCreate):
        return store.create_project(body.name)

    @app.get("/api/projects/{project_id}")
    def project(project_id: str):
        return store.project(project_id)

    @app.put("/api/projects/{project_id}/template")
    def update_template(project_id: str, body: Template):
        return store.update_template(project_id, body.model_dump())

    @app.post("/api/projects/{project_id}/sources")
    async def source(project_id: str, file: UploadFile = File(...)):
        store.project(project_id)
        try:
            data = await file.read(MAX_UPLOAD_BYTES + 1)
            if len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Source exceeds the 5 MB upload limit.")
            filename = Path((file.filename or "").replace("\\", "/")).name
            if not filename or len(filename) > 240:
                raise HTTPException(422, "Source filename is required and must be at most 240 characters.")
            parsed = parse_source(filename, data)
            return store.import_source(project_id, filename, data, parsed)
        finally:
            await file.close()

    @app.post("/api/projects/{project_id}/preview", status_code=201)
    def preview(project_id: str, body: PreviewRequest):
        return store.preview(project_id, body.expected_revision)

    @app.get("/api/projects/{project_id}/generations/{generation_id}")
    def generation(project_id: str, generation_id: str):
        return store.generation(project_id, generation_id)

    @app.post("/api/projects/{project_id}/generations/{generation_id}/approve")
    def approve(project_id: str, generation_id: str, body: ApproveRequest):
        return store.approve(project_id, generation_id, body.expected_revision, body.actor, body.acknowledge_warnings)

    @app.post("/api/projects/{project_id}/generations/{generation_id}/reject")
    def reject(project_id: str, generation_id: str, body: RejectRequest):
        return store.reject(project_id, generation_id, body.actor)

    @app.get("/api/projects/{project_id}/generations/{generation_id}/export")
    def export(project_id: str, generation_id: str):
        content = store.export(project_id, generation_id)
        return Response(content, media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="FigureRelay-{generation_id}.zip"'})

    @app.post("/api/demo", status_code=201)
    def demo():
        project = store.create_project("Quarterly business review", DEMO_TEMPLATE)
        return store.import_source(project["id"], "quarterly-v1.csv", DEMO_V1, parse_source("quarterly-v1.csv", DEMO_V1))

    @app.post("/api/projects/{project_id}/demo-revision")
    def demo_revision(project_id: str):
        return store.import_source(project_id, "quarterly-v2.csv", DEMO_V2, parse_source("quarterly-v2.csv", DEMO_V2))

    frontend = Path(os.environ.get("FIGURERELAY_FRONTEND_DIR", str(project_root / "frontend" / "dist")))
    if frontend.is_dir() and (frontend / "index.html").is_file():
        # All API routes are registered first. Missing API paths retain JSON 404s.
        @app.api_route("/api/{missing:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        def unknown_api(missing: str):
            raise HTTPException(404, "API endpoint was not found.")

        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    else:
        @app.get("/")
        def frontend_unbuilt():
            return {"application": "FigureRelay", "message": "Build the frontend to open the workspace here.", "api_docs": "/api/docs"}
    return app
