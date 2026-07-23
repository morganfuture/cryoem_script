#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
desymmetrize_star.py
--------------------
Reverse a RELION Cn symmetry expansion by keeping only the FIRST occurrence
of each original particle (identified by ImageName + MicrographName).

For a C2-expanded file every original particle appears exactly twice with the
same ImageName / MicrographName but different AngleRot.  Selecting the first
occurrence recovers one asymmetric unit per particle and allows reconstruction
of the whole-particle map.

The ouput desymmetrized particle file can be used for homogenous or non-uniform refinement.

Usage:
    python desymmetrize_star.py <input.star> [output.star]

If output path is omitted the script writes  <input_stem>_desym.star  next to
the input file.

Author:  Aimin Cheng

"""

import sys
import os
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal RELION STAR parser
# ---------------------------------------------------------------------------

def parse_star(path: str) -> list[dict]:
    """
    Parse a RELION-format STAR file and return a list of data blocks.

    Each block is a dict:
        {
            "name":    str,           # e.g. "optics", "particles"
            "header":  list[str],     # raw lines before the column labels
            "columns": list[str],     # _rlnXxx column names, in order
            "rows":    list[str],     # raw data lines (one per particle)
        }

    Lines that belong to no named block (e.g. the leading "# version 50001"
    lines) are stored in a synthetic block with name="" so they can be
    faithfully reproduced in the output.
    """
    blocks: list[dict] = []

    with open(path, "r") as fh:
        lines = fh.readlines()

    current: dict | None = None
    in_loop = False
    in_columns = False

    def flush():
        if current is not None:
            blocks.append(current)

    preamble_lines: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── new data block ──────────────────────────────────────────────────
        if stripped.startswith("data_"):
            flush()
            # Attach any accumulated preamble lines to this block's header
            current = {
                "name": stripped[len("data_"):],
                "header": list(preamble_lines),
                "columns": [],
                "rows": [],
            }
            preamble_lines = []
            in_loop = False
            in_columns = False
            i += 1
            continue

        # ── loop_ keyword ───────────────────────────────────────────────────
        if stripped == "loop_":
            if current is None:
                # loop before any data_ block – shouldn't happen but handle it
                current = {"name": "", "header": list(preamble_lines),
                           "columns": [], "rows": []}
                preamble_lines = []
            current["header"].append(line)
            in_loop = True
            in_columns = True
            i += 1
            continue

        # ── column labels (_rln…) ───────────────────────────────────────────
        if in_loop and in_columns and stripped.startswith("_rln"):
            col_name = stripped.split()[0]   # drop the "#N" index
            current["columns"].append(col_name)
            current["header"].append(line)
            i += 1
            continue

        # ── data rows ───────────────────────────────────────────────────────
        if in_loop and in_columns and stripped and not stripped.startswith("#") \
                and not stripped.startswith("_"):
            in_columns = False  # first non-label line ends the column section
            current["rows"].append(line)
            i += 1
            continue

        if in_loop and not in_columns and stripped and \
                not stripped.startswith("data_"):
            current["rows"].append(line)
            i += 1
            continue

        # ── everything else (blank lines, comments, version tags) ───────────
        if current is None:
            preamble_lines.append(line)
        else:
            # blank / comment line between blocks → treat as preamble for
            # the *next* block, or append to header if loop not started yet
            if not in_loop:
                current["header"].append(line)
            else:
                # blank line after data rows → separator before next block
                preamble_lines.append(line)
        i += 1

    flush()
    # If there were trailing lines with no subsequent data_ block
    if preamble_lines:
        blocks.append({"name": "__trailing__", "header": preamble_lines,
                       "columns": [], "rows": []})

    return blocks


def write_star(blocks: list[dict], path: str) -> None:
    """Write parsed blocks back to a STAR file."""
    with open(path, "w") as fh:
        for block in blocks:
            # Header lines (includes "# version …", "data_xxx", "loop_",
            # and "_rlnXxx #N" labels)
            for line in block["header"]:
                fh.write(line)
            # Data rows
            for row in block["rows"]:
                fh.write(row)


# ---------------------------------------------------------------------------
# De-duplication
# ---------------------------------------------------------------------------

def desymmetrize_particles(block: dict) -> dict:
    """
    Return a new particles block containing only the first occurrence of each
    original particle.

    Identity key = (ImageName, MicrographName), i.e. columns
    _rlnImageName and _rlnMicrographName.
    These two fields are always the first two columns in RELION particle
    star files, but we look them up by name to be safe.
    """
    cols = block["columns"]

    try:
        img_idx  = cols.index("_rlnImageName")
        mic_idx  = cols.index("_rlnMicrographName")
    except ValueError as e:
        raise RuntimeError(
            "Could not find _rlnImageName or _rlnMicrographName in the "
            f"particles block columns.\nColumns found: {cols}"
        ) from e

    seen: set[tuple[str, str]] = set()
    kept_rows: list[str] = []
    total = 0
    skipped = 0

    for raw_line in block["rows"]:
        stripped = raw_line.strip()
        if not stripped:           # preserve blank separator lines
            kept_rows.append(raw_line)
            continue

        total += 1
        fields = stripped.split()

        if len(fields) <= max(img_idx, mic_idx):
            # Malformed line – keep it and warn
            print(f"WARNING: short line ({len(fields)} fields), keeping: "
                  f"{stripped[:80]}…", file=sys.stderr)
            kept_rows.append(raw_line)
            continue

        key = (fields[img_idx], fields[mic_idx])

        if key in seen:
            skipped += 1
            continue

        seen.add(key)
        kept_rows.append(raw_line)

    print(f"  Total particle lines  : {total}")
    print(f"  Kept (first occurrence): {total - skipped}")
    print(f"  Removed (duplicates)  : {skipped}")

    new_block = dict(block)      # shallow copy – reuse header/columns
    new_block["rows"] = kept_rows
    return new_block


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path  = sys.argv[1]
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        stem        = Path(input_path).stem
        parent      = Path(input_path).parent
        output_path = str(parent / f"{stem}_desym.star")

    print(f"Input  : {input_path}")
    print(f"Output : {output_path}")
    print("Parsing STAR file …")

    blocks = parse_star(input_path)

    print(f"Found {len(blocks)} data block(s): "
          f"{[b['name'] for b in blocks]}")

    # Find and process the particles block
    processed_blocks = []
    found_particles = False
    for block in blocks:
        if block["name"] == "particles":
            print("Processing particles block …")
            block = desymmetrize_particles(block)
            found_particles = True
        processed_blocks.append(block)

    if not found_particles:
        print("WARNING: no 'data_particles' block found – output is a copy "
              "of the input.", file=sys.stderr)

    print("Writing output …")
    write_star(processed_blocks, output_path)
    print("Done.")


if __name__ == "__main__":
    main()
