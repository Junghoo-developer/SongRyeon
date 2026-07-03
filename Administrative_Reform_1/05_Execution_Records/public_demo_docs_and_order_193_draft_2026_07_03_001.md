# Public Demo Docs And ORDER 193 Draft 2026-07-03 001

## Purpose

After the Vessel graph memory and R traversal baseline was merged to `main`, the public-facing documentation needed to reflect what the project can actually demonstrate.

This record documents the documentation-only follow-up.

## Changes

- Updated `README.md` so the new graph memory/Vessel/R traversal baseline is visible near the top.
- Added `DEMO.md` with stable public demo commands.
- Added `RELEASE_NOTES.md` for the 2026-07-03 Vessel/R traversal baseline.
- Added `ORDER_193_R_RESULT_TO_NODE3_VESSEL_MATERIAL_V0.md` as the next proposed MVP.
- Updated `04_Orders/README.md` so ORDER 193 is discoverable.

## Boundaries

No runtime code was changed.

No new graph memory behavior was implemented.

No R route was connected to normal live chat.

## Verification

Documentation-only pass:

```text
git diff --check
```
