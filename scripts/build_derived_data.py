#!/usr/bin/env python3
"""Compatibility shim for the derived data pipeline.

Heavy implementation lives in ``derived_pipeline.py``.
This module preserves historical imports and script entrypoint.
"""

from __future__ import annotations

import derived_pipeline as _impl

globals().update({k: v for k, v in vars(_impl).items() if not k.startswith("__")})
build_derived_data = _impl.build_derived_data


if __name__ == "__main__":
    build_derived_data()
