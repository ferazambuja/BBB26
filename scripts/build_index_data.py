#!/usr/bin/env python3
"""Compatibility shim for index data builder.

Heavy implementation lives in ``builders/index_data_builder.py``.
This module keeps backward-compatible imports and script entrypoint.
"""

from __future__ import annotations

import builders.index_data_builder as _impl

globals().update({k: v for k, v in vars(_impl).items() if not k.startswith("__")})
write_index_data = _impl.write_index_data


if __name__ == "__main__":
    write_index_data()
