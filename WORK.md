---
this_file: WORK.md
---

# Work log

## 2026-10-14 — CLI scaling and placement

- Added `--scale` (relative multiplier), `--size` (absolute artwork viewport
  size in canvas units), `--x_off` and `--y_off` to both CLI conversion commands.
  Scaling is centred; offsets apply afterward; the frame and clip stay fixed.
- Added configurable batch suffixes and same-folder rerun filtering. Failed
  batch items now cause a nonzero exit status.
- Wrote executable `task301/oldicons/iconify.sh`, defaulting to 80% scale and
  creating `fontlab8-icon.svg`, `pad2-icon.svg` and `transtype5-icon.svg` beside
  their sources. The script runs from any working directory using this checkout.
- Verified five wrapper-script invocations in an isolated directory: default,
  offsets, relative override, absolute override, and space-separated arguments.
  All passed; reruns produced no `-icon-icon.svg` files.
- Full suite: 26 passed. Core and new placement tests pass Ruff; changed CLI
  passes with only its existing builtin-shadowing, lazy-import and boolean
  positional-argument rules excluded. `git diff --check` passed.
- Rendered all three saved 80% icons with resvg, inspected them, and compared
  complete artwork subtrees. Original file hashes match the previous report.

## 2026-10-14 — Existing SVG icon conversion

- Converted all three `task301/oldicons` SVGs to `task301/icons/*_glass.svg`
  using the batch CLI with ultra quality (32 bevel steps).
- Fixed payload import to preserve the complete SVG and scale its viewport;
  the original implementation discarded definitions and clipped unscaled artwork.
- Fixed duplicate theme gradient IDs, invalid SVG attribute spelling, and
  lxml element truth testing that skipped the rendered outer element.
- Added regression coverage for complex artwork, intrinsic pixel dimensions,
  large inline SVGs, gradient replacement and SVG attributes.
- Baseline: 7 tests passed. After changes: 11 tests passed.
- Rendered every original and generated SVG with resvg and inspected the results:
  all original symbols and colours remain visible inside rounded glass borders.
- Verification report and a side-by-side preview are saved with the output icons.
- Ruff's existing FBT001/FBT002 warnings concern boolean positional arguments in
  `SVGProcessor`; those API signatures are unchanged by this work.
