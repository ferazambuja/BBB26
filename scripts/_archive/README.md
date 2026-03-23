# scripts/_archive

Archived: 2026-03-23

Reason: Replaced by Claude Code headless vision pipeline (`deploy/votalhada_claude_update.sh`).
The Tesseract-based OCR approach was superseded by Claude vision for parsing Votalhada
poll screenshots.

## Contents

| File | Purpose |
|------|---------|
| `votalhada_ocr_feasibility.py` | Feasibility parser for Votalhada Consolidado OCR (Tesseract-based, validate-only) |
| `votalhada_ocr_batch_validate.py` | Batch validation runner across all paredao images |
| `votalhada_auto_update.py` | Local OCR auto-update runner (fetch, parse, validate, gated apply to polls.json) |
| `votalhada_platform_consistency_audit.py` | Audit consistency of platform cards against source rows |

Corresponding test files archived in `tests/_archive/`.

## Restore

```bash
git mv scripts/_archive/<filename>.py scripts/<filename>.py
```
