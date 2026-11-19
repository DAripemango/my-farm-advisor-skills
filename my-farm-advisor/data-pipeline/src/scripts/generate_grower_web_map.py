#!/usr/bin/env python3
"""CLI entrypoint for the data-pipeline grower web-map subskill.

The implementation lives in ``data-pipeline/grower-web-map/src``.  When this
entrypoint is seeded into the runtime, the implementation sits beside it; in a
checkout it is resolved relative to the skill root or via
``reporting_bootstrap.ensure_skill_path``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_LOCAL_DIR = Path(__file__).resolve().parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))

try:  # runtime-local seed or same-directory copy
    from grower_web_map import main
except ImportError:  # pragma: no cover - checkout path
    _CHECKOUT_SKILL_ROOT = Path(__file__).resolve().parents[3]
    _CHECKOUT_SUBSKILL_SRC = (
        _CHECKOUT_SKILL_ROOT / "data-pipeline" / "grower-web-map" / "src"
    )
    if _CHECKOUT_SUBSKILL_SRC.is_dir():
        sys.path.insert(0, str(_CHECKOUT_SUBSKILL_SRC))
    else:
        from reporting_bootstrap import ensure_skill_path

        ensure_skill_path("grower-web-map")
    from grower_web_map import main


if __name__ == "__main__":
    raise SystemExit(main())
