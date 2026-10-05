import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import ifc_fixture  # noqa: E402
from Schependomlaan.config import make_settings  # noqa: E402
from Schependomlaan.run_pipeline import Pipeline  # noqa: E402


@pytest.fixture(scope="session")
def fixture_ifc(tmp_path_factory):
    return ifc_fixture.build(str(tmp_path_factory.mktemp("ifc") / "fixture.ifc"))


@pytest.fixture(scope="session")
def pipe(tmp_path_factory, fixture_ifc):
    ds = tmp_path_factory.mktemp("ds")
    p = Pipeline(make_settings(ds, fixture_ifc))
    p.run("all")
    return p


def load(pipe, key):
    return json.loads(pipe.path(key).read_text())
