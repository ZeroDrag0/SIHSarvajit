import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

client = TestClient(app)
CLIENT_TS = (config.REPO_ROOT / "web" / "src" / "api" / "client.ts").read_text(encoding="utf-8")


def test_endpoints_match_frontend_contract():
    """Every {api, file} pair in web/src/api/client.ts must be served by the backend."""
    pairs = dict(re.findall(r"api: '([^']+)', file: '([^']+)'", CLIENT_TS))
    assert len(pairs) == 12
    assert {p: f for p, (f, _) in config.ENDPOINTS.items()} == pairs


@pytest.mark.parametrize("path,spec", list(config.ENDPOINTS.items()))
def test_serves_pipeline_file_unchanged(path, spec):
    rel, media = spec
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(media)
    assert r.content == (config.PROCESSED / rel).read_bytes()


def test_json_endpoints_parse():
    for path, (_, media) in config.ENDPOINTS.items():
        if media == "application/json":
            json.loads(client.get(path).text)


def test_health_ok():
    assert client.get("/api/health").json() == {"status": "ok", "missing_files": []}


def test_missing_file_is_404(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PROCESSED", tmp_path)
    assert client.get("/api/building").status_code == 404
    assert client.get("/api/health").json()["status"] == "degraded"


def test_run_refused_without_ifc(monkeypatch):
    monkeypatch.delenv("SCHEP_IFC", raising=False)
    monkeypatch.setattr(config, "RAW_IFC_DIR", Path("/nonexistent"))
    r = client.post("/api/pipeline/run", json={"stage": "all"})
    assert r.status_code == 409 and "IFC" in r.json()["detail"]


def test_run_rejects_unknown_stage():
    assert client.post("/api/pipeline/run", json={"stage": "rm -rf"}).status_code in (409, 422)


def test_upload_rejects_non_ifc():
    assert client.post("/api/pipeline/ifc", files={"file": ("x.txt", b"hi")}).status_code == 422


def test_status_shape():
    s = client.get("/api/pipeline/status").json()
    assert s["published_source_mode"] == "live_ifc" and s["published_ifc_spaces"] == 100
