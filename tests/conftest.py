"""Shared test setup.

The ``api`` package is independent of Home Assistant.  To test it without
installing Home Assistant it is imported under the name ``leapmotor_api``,
which avoids executing the integration's ``__init__`` (that one needs HA).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "custom_components" / "leapmotor_cloud" / "api"

if "leapmotor_api" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "leapmotor_api", API_DIR / "__init__.py", submodule_search_locations=[str(API_DIR)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["leapmotor_api"] = module
    spec.loader.exec_module(module)
