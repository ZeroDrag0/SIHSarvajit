"""Runs the Schependomlaan pipeline as a subprocess and publishes its output.

Safety: a run never writes into the live processed/ folder. It works on a staging copy of the dataset
root, and the result is promoted only if the pipeline really read an IFC (source_mode == live_ifc).
Without an IFC the pipeline would fall back to a cached inspection and overwrite good outputs with
degraded ones, so the runner refuses to start instead.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from . import config

STAGES = ["inspect", "preprocess", "classify", "floors", "units", "geometry", "pointcloud", "cadastral",
          "terrain", "validate", "ulpin", "export", "all"]

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def find_ifc() -> Path | None:
    env = os.environ.get("SCHEP_IFC")
    for c in ([Path(env)] if env else []) + sorted(config.RAW_IFC_DIR.glob("*.ifc")):
        if c.is_file():
            return c.resolve()
    return None


def status() -> dict[str, Any]:
    report = config.PROCESSED / "pipeline_report.json"
    last = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    ifc = find_ifc()
    running = next((j for j in _jobs.values() if j["state"] == "running"), None)
    return {
        "ifc_available": ifc is not None,
        "ifc_file": ifc.name if ifc else None,
        "published_source_mode": last.get("source_mode"),
        "published_ifc_spaces": last.get("ifc_spaces"),
        "published_property_units": last.get("inferred_property_units"),
        "processed_updated_at": report.stat().st_mtime if report.exists() else None,
        "running_job": running["id"] if running else None,
        "stages": STAGES,
    }


def start(stage: str) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"unknown stage '{stage}'")
    ifc = find_ifc()
    if ifc is None:
        raise LookupError("No IFC file available. Upload one via POST /api/pipeline/ifc or place it in "
                          "pipeline/Schependomlaan/raw/ifc/ (re-running without it would only produce degraded cached output).")
    with _lock:
        if any(j["state"] == "running" for j in _jobs.values()):
            raise RuntimeError("A pipeline run is already in progress.")
        job = {"id": uuid.uuid4().hex[:12], "stage": stage, "state": "running", "started": time.time(),
               "finished": None, "log": "", "error": None}
        _jobs[job["id"]] = job
    threading.Thread(target=_run, args=(job, ifc), daemon=True).start()
    return job


def get(job_id: str) -> dict[str, Any] | None:
    return _jobs.get(job_id)


def _run(job: dict[str, Any], ifc: Path) -> None:
    stage_dir = Path(tempfile.mkdtemp(prefix="verticad_run_"))
    try:
        root = stage_dir / "Schependomlaan"
        # staging copy: previous outputs (so single stages can reuse upstream artefacts) + optional inputs
        shutil.copytree(config.DATASET_ROOT, root, ignore=shutil.ignore_patterns("raw", "__pycache__"))
        cmd = [sys.executable, "-m", "Schependomlaan.run_pipeline", "--stage", job["stage"],
               "--ifc", str(ifc), "--dataset-root", str(root)]
        if config.RAW_PC_DIR.is_dir() and any(config.RAW_PC_DIR.rglob("*")):
            cmd += ["--pointcloud-dir", str(config.RAW_PC_DIR)]
        env = {**os.environ, "PYTHONPATH": str(config.PIPELINE_SRC)}
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=3600)
        job["log"] = (proc.stdout + proc.stderr)[-8000:]
        if proc.returncode != 0:
            raise RuntimeError(f"pipeline exited with code {proc.returncode}")
        report = json.loads((root / "processed" / "pipeline_report.json").read_text(encoding="utf-8"))
        if report.get("source_mode") != "live_ifc":
            raise RuntimeError(f"pipeline ran in '{report.get('source_mode')}' mode, not live_ifc; outputs not published")
        _publish(root / "processed")
        job["state"] = "done"
    except Exception as exc:  # noqa: BLE001 - surfaced to the client
        job["state"], job["error"] = "failed", str(exc)
    finally:
        job["finished"] = time.time()
        shutil.rmtree(stage_dir, ignore_errors=True)


def _publish(new_processed: Path) -> None:
    """Swap the processed folder in one rename so readers never see a half-written dataset."""
    live, backup, incoming = config.PROCESSED, config.PROCESSED.with_name("processed.prev"), config.PROCESSED.with_name("processed.new")
    shutil.rmtree(incoming, ignore_errors=True)
    shutil.copytree(new_processed, incoming)
    shutil.rmtree(backup, ignore_errors=True)
    live.rename(backup)
    incoming.rename(live)
