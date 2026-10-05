from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "Schependomlaan"
ARCHIVE_ROOT = (PROJECT_ROOT.parent.parent / "Archive-DataSetSchependomlaan").resolve()
RULES_PATH = Path(__file__).with_name("rules.yaml")

PROCESSED_SUBDIRS = ["ifc", "floors", "apartments", "geometry", "pointcloud",
                     "cadastral", "validation", "ulpin", "cadastre"]


def load_rules(path: Path | None = None) -> dict:
    return yaml.safe_load((path or RULES_PATH).read_text(encoding="utf-8"))


@dataclass
class PipelineSettings:
    dataset_root: Path = DEFAULT_DATASET_ROOT
    ifc_path: Path | None = None
    pointcloud_dir: Path | None = None
    rules: dict = field(default_factory=load_rules)

    # ---- directories -------------------------------------------------
    @property
    def raw_dir(self) -> Path: return self.dataset_root / "raw"
    @property
    def external_dir(self) -> Path: return self.dataset_root / "external"
    @property
    def processed_dir(self) -> Path: return self.dataset_root / "processed"

    def out(self, *parts: str) -> Path:
        return self.processed_dir.joinpath(*parts)

    # ---- source discovery (never downloads anything) ------------------
    def resolve_ifc(self) -> Path | None:
        candidates: list[Path] = []
        if self.ifc_path:
            candidates.append(Path(self.ifc_path))
        if os.environ.get("SCHEP_IFC"):
            candidates.append(Path(os.environ["SCHEP_IFC"]))
        candidates += sorted((self.raw_dir / "ifc").glob("*.ifc"))
        candidates.append(ARCHIVE_ROOT / "Design model IFC" / "IFC Schependomlaan.ifc")
        for c in candidates:
            if c.is_file():
                return c.resolve()
        return None

    def resolve_pointcloud_dir(self) -> Path | None:
        candidates: list[Path] = []
        if self.pointcloud_dir:
            candidates.append(Path(self.pointcloud_dir))
        if os.environ.get("SCHEP_POINTCLOUD_DIR"):
            candidates.append(Path(os.environ["SCHEP_POINTCLOUD_DIR"]))
        candidates += [self.raw_dir / "pointcloud", ARCHIVE_ROOT / "Point Clouds"]
        for c in candidates:
            if c.is_dir() and any(c.rglob("*")):
                return c.resolve()
        return None

    def ensure_directories(self) -> None:
        for d in (self.raw_dir, self.external_dir):
            d.mkdir(parents=True, exist_ok=True)
        for sub in PROCESSED_SUBDIRS:
            (self.processed_dir / sub).mkdir(parents=True, exist_ok=True)


def make_settings(dataset_root: str | Path | None = None, ifc: str | Path | None = None,
                  pointcloud_dir: str | Path | None = None) -> PipelineSettings:
    return PipelineSettings(
        dataset_root=Path(dataset_root).resolve() if dataset_root else DEFAULT_DATASET_ROOT,
        ifc_path=Path(ifc) if ifc else None,
        pointcloud_dir=Path(pointcloud_dir) if pointcloud_dir else None,
    )


project_settings = make_settings()


def ensure_directories() -> None:
    project_settings.ensure_directories()
