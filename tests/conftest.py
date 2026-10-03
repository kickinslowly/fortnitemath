import json
import shutil
from pathlib import Path

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "order-of-ops-exponents"


@pytest.fixture(scope="session")
def gen():
    return load_generator(CID)


@pytest.fixture(scope="session")
def baked():
    with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def tmp_repo(tmp_path):
    """A throwaway repo root holding a copy of the real cartridge and maps."""
    shutil.copytree(REPO_ROOT / "cartridges" / CID, tmp_path / "cartridges" / CID)
    shutil.copytree(REPO_ROOT / "maps", tmp_path / "maps",
                    ignore=shutil.ignore_patterns("generated"))
    shutil.copytree(REPO_ROOT / "console" / "verse", tmp_path / "console" / "verse",
                    ignore=shutil.ignore_patterns("generated"))
    return tmp_path


def write_json(path: Path, data):
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
