"""VERTICAD backend: serves the pipeline's outputs to the web app and drives the pipeline itself."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, pipeline_runner

app = FastAPI(title="VERTICAD API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"])


def _serve(rel: str, media: str) -> FileResponse:
    path = config.PROCESSED / rel
    if not path.is_file():
        raise HTTPException(404, f"{rel} not found - run the pipeline (POST /api/pipeline/run) or restore processed/")
    # revalidate every time so a pipeline re-run shows up without a server restart
    return FileResponse(path, media_type=media, headers={"Cache-Control": "no-cache"})


def _register(api_path: str, rel: str, media: str) -> None:
    app.add_api_route(api_path, lambda: _serve(rel, media), methods=["GET"], name=api_path, include_in_schema=True)


for _p, (_rel, _media) in config.ENDPOINTS.items():
    _register(_p, _rel, _media)


@app.get("/api/health")
def health() -> dict:
    missing = [rel for rel, _ in config.ENDPOINTS.values() if not (config.PROCESSED / rel).is_file()]
    return {"status": "ok" if not missing else "degraded", "missing_files": missing}


@app.get("/api/pipeline/status")
def pipeline_status() -> dict:
    return pipeline_runner.status()


class RunRequest(BaseModel):
    stage: str = "all"


@app.post("/api/pipeline/run", status_code=202)
def pipeline_run(req: RunRequest) -> dict:
    try:
        return pipeline_runner.start(req.stage)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except LookupError as e:
        raise HTTPException(409, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e


@app.get("/api/pipeline/jobs/{job_id}")
def pipeline_job(job_id: str) -> dict:
    job = pipeline_runner.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    return job


@app.post("/api/pipeline/ifc")
def upload_ifc(file: UploadFile = File(...)) -> dict:
    if not (file.filename or "").lower().endswith(".ifc"):
        raise HTTPException(422, "expected a .ifc file")
    config.RAW_IFC_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.RAW_IFC_DIR / "uploaded.ifc"  # fixed name: never trust client paths
    tmp = dest.with_suffix(".part")
    size = 0
    with tmp.open("wb") as out:
        while chunk := file.file.read(1 << 20):
            size += len(chunk)
            if size > config.MAX_IFC_BYTES:
                out.close()
                tmp.unlink(missing_ok=True)
                raise HTTPException(413, "IFC file too large")
            out.write(chunk)
    for old in config.RAW_IFC_DIR.glob("*.ifc"):
        old.unlink()
    tmp.rename(dest)
    return {"stored": dest.name, "bytes": size}


# Serve the built web app from the same origin (production). API routes above take precedence.
if (config.WEB_DIST / "index.html").is_file():
    app.mount("/", StaticFiles(directory=config.WEB_DIST, html=True), name="web")
