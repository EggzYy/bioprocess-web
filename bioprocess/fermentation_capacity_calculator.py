"""Package wrapper for the original fermentation_capacity_calculator module.

This thin wrapper loads the legacy `fermentation_capacity_calculator.py`
from the repository root so that its classes and functions are available
under the `bioprocess` package namespace. Tests and internal modules expect
`bioprocess.fermentation_capacity_calculator` to exist, but the historical
implementation lives at the project root. This file bridges that gap without
modifying the original module.
"""

from importlib import util as _util
from pathlib import Path as _Path

_root = _Path(__file__).resolve().parent.parent / "fermentation_capacity_calculator.py"
_spec = _util.spec_from_file_location("fermentation_capacity_calculator", _root)
_module = _util.module_from_spec(_spec)
import sys as _sys
assert _spec and _spec.loader
_sys.modules["fermentation_capacity_calculator"] = _module
_spec.loader.exec_module(_module)

globals().update({k: getattr(_module, k) for k in dir(_module) if not k.startswith("__")})

__all__ = [k for k in globals().keys() if not k.startswith("_")]
