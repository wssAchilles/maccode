"""Optional native compute backend discovery for rolling feature kernels."""

from __future__ import annotations

import importlib
import logging
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType

from config import Config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NativeBackendStatus:
    """Current native backend preference and availability."""

    preferred_backend: str
    active_backend: str
    native_enabled: bool
    native_available: bool
    module_name: str
    reason: str


def _native_module_name() -> str:
    return str(getattr(Config, 'COMPUTE_NATIVE_MODULE', 'rolling_features_native')).strip() or 'rolling_features_native'


def _native_module_root() -> Path:
    return Path(__file__).resolve().parent.parent / 'native' / 'rolling_features'


def _ensure_native_search_path() -> None:
    native_root = _native_module_root()
    candidate_paths = (
        native_root,
        native_root / 'build',
    )
    for candidate in candidate_paths:
        candidate_str = str(candidate)
        if candidate.exists() and candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


@lru_cache(maxsize=1)
def load_native_module() -> ModuleType | None:
    """Load the optional pybind11 module when it is locally available."""

    _ensure_native_search_path()
    module_name = _native_module_name()
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        logger.info('Native compute module unavailable (%s): %s', module_name, exc)
        return None


def get_native_backend_status() -> NativeBackendStatus:
    """Return the native backend status used by profiling and dashboard surfaces."""

    native_enabled = bool(getattr(Config, 'COMPUTE_NATIVE_ENABLED', False))
    module_name = _native_module_name()
    module = load_native_module()
    native_available = module is not None

    if native_enabled and native_available:
        return NativeBackendStatus(
            preferred_backend='native_cpp',
            active_backend='native_cpp',
            native_enabled=True,
            native_available=True,
            module_name=module_name,
            reason='Native rolling feature backend is available',
        )

    if native_enabled and not native_available:
        return NativeBackendStatus(
            preferred_backend='native_cpp',
            active_backend='python_pandas',
            native_enabled=True,
            native_available=False,
            module_name=module_name,
            reason='Native backend requested but module is not installed',
        )

    return NativeBackendStatus(
        preferred_backend='python_pandas',
        active_backend='python_pandas',
        native_enabled=False,
        native_available=native_available,
        module_name=module_name,
        reason='Native backend disabled by configuration',
    )

