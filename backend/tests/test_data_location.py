# Copyright 2026 Dhruba Poudel
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

import figurerelay.app as app_module


@pytest.mark.parametrize("platform,setting,relative", [
    ("win32", "LOCALAPPDATA", ("local-app-data", "FigureRelay")),
    ("darwin", None, ("home", "Library", "Application Support", "FigureRelay")),
    ("linux", "XDG_DATA_HOME", ("xdg-data", "FigureRelay")),
    ("linux", None, ("home", ".local", "share", "FigureRelay")),
])
def test_installed_package_uses_user_data_and_reopens_persisted_project(tmp_path, monkeypatch, platform, setting, relative):
    monkeypatch.setattr(app_module.sys, "platform", platform)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.delenv("FIGURERELAY_DATA_DIR", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    if setting:
        monkeypatch.setenv(setting, str(tmp_path / relative[0]))
    # Simulate a non-editable installation; the package tree is not a data root.
    package_file = tmp_path / "read-only-python" / "site-packages" / "figurerelay" / "app.py"
    monkeypatch.setattr(app_module, "__file__", str(package_file))
    expected = tmp_path.joinpath(*relative)
    with TestClient(app_module.create_app(), base_url="http://127.0.0.1:8080") as client:
        assert client.app.state.store.data_dir == expected
        project = client.post("/api/projects", json={"name": "Persistent installed app"}).json()
        assert client.app.state.store.path.is_file()
    with TestClient(app_module.create_app(), base_url="http://127.0.0.1:8080") as reopened:
        saved = reopened.get(f"/api/projects/{project['id']}")
        assert saved.status_code == 200
        assert saved.json()["name"] == "Persistent installed app"
    assert not (tmp_path / "read-only-python").exists()


def test_windows_fallback_and_relative_xdg_setting_use_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(app_module.sys, "platform", "win32")
    assert app_module.default_data_dir() == tmp_path / "home" / "AppData" / "Local" / "FigureRelay"
    monkeypatch.setattr(app_module.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "relative-directory")
    assert app_module.default_data_dir() == tmp_path / "home" / ".local" / "share" / "FigureRelay"


def test_explicit_and_environment_data_directories_override_user_default(tmp_path, monkeypatch):
    monkeypatch.setenv("FIGURERELAY_DATA_DIR", str(tmp_path / "environment"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "unused-default"))
    environment_app = app_module.create_app()
    assert environment_app.state.store.data_dir == tmp_path / "environment"
    explicit_app = app_module.create_app(tmp_path / "explicit")
    assert explicit_app.state.store.data_dir == tmp_path / "explicit"
    assert not (tmp_path / "unused-default").exists()
