#!/usr/bin/env python3
"""Compatibility shim for index data builder.

Heavy implementation lives in ``builders/index_data_builder.py``.
This module keeps backward-compatible imports and script entrypoint.
"""

from __future__ import annotations

from builders.index_data_builder import build_index_data, write_index_data

__all__ = ["build_index_data", "write_index_data"]


if __name__ == "__main__":
    write_index_data()
