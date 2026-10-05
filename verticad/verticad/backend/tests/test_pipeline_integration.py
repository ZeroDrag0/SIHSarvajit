"""End to end: upload IFC -> run model -> outputs published -> API serves the new data.
Uses the pipeline's own synthetic IFC fixture on a temp copy of the dataset (the real one is untouched)."""
import json
import shutil
import sys
import time

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

sys.path.insert(0, str(config.REPO_ROOT / "pipeline" / "tests" / "Schependomlaan"))
import ifc_fixture  # noqa: E402


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    root = tmp_path / "Schependomlaan"
    shutil.copytree(config.DATASET_ROOT, root)
    monkeypatch.setattr(config, "DATASET_ROOT", root)
    monkeypatch.setattr(config, "PROCESSED", root / "processed")
    monkeypatch.setattr(config, "RAW_IFC_DIR", root / "raw" / "ifc")
    monkeypatch.setattr(config, "RAW_PC_DIR", root / "raw" / "pointcloud")
    monkeypatch.delenv("SCHEP_IFC", raising=False)
    return root


def _wait(client, job_id, timeout=300):
    end = time.time() + timeout
    while time.time() < end:
        job = client.get(f"/api/pipeline/jobs/{job_id}").json()
        if job["state"] != "running":
            return job
        time.sleep(0.5)
    raise TimeoutError


def test_upload_run_publish(sandbox, tmp_path):
    client = TestClient(app)
    before = client.get("/api/metrics").json()
    ifc = ifc_fixture.build(str(tmp_path / "fixture.ifc"))
    with open(ifc, "rb") as f:
        assert client.post("/api/pipeline/ifc", files={"file": ("fixture.ifc", f)}).status_code == 200
    assert client.get("/api/pipeline/status").json()["ifc_available"] is True

    r = client.post("/api/pipeline/run", json={"stage": "all"})
    assert r.status_code == 202
    job = _wait(client, r.json()["id"])
    assert job["state"] == "done", job["error"] or job["log"]

    after = client.get("/api/metrics").json()
    assert after["source_mode"] == "live_ifc"
    assert after["ifc_spaces"] != before["ifc_spaces"]            # fixture model differs from Schependomlaan
    assert client.get("/api/health").json()["status"] == "ok"      # every contract file present after publish
    units = client.get("/api/units").json()
    assert units is not None
    assert (sandbox / "processed.prev").is_dir()                   # previous outputs kept as backup


def test_failed_run_keeps_published_data(sandbox):
    client = TestClient(app)
    sandbox.joinpath("raw", "ifc").mkdir(parents=True, exist_ok=True)
    (sandbox / "raw" / "ifc" / "broken.ifc").write_text("not an ifc")
    before = (config.PROCESSED / "pipeline_report.json").read_bytes()
    r = client.post("/api/pipeline/run", json={"stage": "all"})
    job = _wait(client, r.json()["id"])
    assert job["state"] == "failed"
    assert (config.PROCESSED / "pipeline_report.json").read_bytes() == before
