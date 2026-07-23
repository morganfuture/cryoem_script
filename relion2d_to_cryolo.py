# -*- coding: utf-8 -*-
"""
Created on Thu May 20 20:42:15 2026

@author: Aimin Cheng

"""

"""
relion2d_to_cryolo.py
---------------------
Convert a RELION selected particles.star (good classes) from 2D-classification 
to cryOLO CBOX / EMAN2 .box format for cryoOLO model training. The customed model
is used further for particle picking .

One output file is created per micrograph, placed under <output_dir>/ with
the same base name as the micrograph and a .cbox or .box extension.

CBOX format (default, recommended for cryOLO ≥ 1.7):
    x_center  y_center  box_width  box_height  confidence  est_box_width
    (tab-separated, no header; origin is top-left, coordinates are box centres)

EMAN2 BOX format (--format box):
    x_corner  y_corner  box_width  box_height
    (tab-separated, no header; x_corner/y_corner are top-left corners)

Usage examples
--------------
# Basic – write .cbox files alongside micrographs, default box size 256
python relion2d_to_cryolo.py particles.star ./cryolo_train/

# Override box size and choose EMAN2 box format
python relion2d_to_cryolo.py particles.star ./cryolo_train/ --box-size 192 --format box

# Read box size from rlnImageSize in the star file (if present)
python relion2d_to_cryolo.py particles.star ./cryolo_train/ --box-size auto

Dependencies: none (stdlib only)
"""

#!/usr/bin/env python3

import argparse
import os
import sys
import re
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# particle STAR file parser
# ---------------------------------------------------------------------------

def parse_star(star_path: str) -> list[dict]:
    """
    Minimal STAR parser that handles one or more data_ blocks.
    Returns a flat list of dicts, one per particle row, using the
    column names as keys (e.g. '_rlnCoordinateX').
    """
    particles = []
    in_loop = False
    columns: list[str] = []
    current_block: dict = {}

    with open(star_path, "r") as fh:
        for raw_line in fh:
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("data_"):
                in_loop = False
                columns = []
                current_block = {}
                continue

            if line == "loop_":
                in_loop = True
                columns = []
                continue

            if in_loop:
                if line.startswith("_rln"):
                    # Column definition: "_rlnFoo  #N"
                    col_name = line.split()[0]
                    columns.append(col_name)
                elif columns:
                    # Data row
                    values = line.split()
                    if len(values) < len(columns):
                        continue  # malformed; skip
                    row = {col: val for col, val in zip(columns, values)}
                    particles.append(row)

    return particles


# ---------------------------------------------------------------------------
# star file checking
# ---------------------------------------------------------------------------

REQUIRED_COLS = {"_rlnCoordinateX", "_rlnCoordinateY", "_rlnMicrographName"}


def validate_columns(particles: list[dict]) -> None:
    if not particles:
        sys.exit("ERROR: No particles found in the STAR file.")
    missing = REQUIRED_COLS - particles[0].keys()
    if missing:
        sys.exit(f"ERROR: Required columns missing from STAR file: {missing}\n"
                 f"       Make sure you are using an *_data.star from a Select job.")


def micrograph_basename(path_str: str) -> str:
    """Return stem of a micrograph path, stripping any directory prefix."""
    return Path(path_str).stem


# ---------------------------------------------------------------------------
# write output file
# ---------------------------------------------------------------------------

def write_cbox(out_path: Path, coords: list[tuple[float, float]], box_size: int) -> None:
    """
    Write a cryOLO CBOX file.
    Columns: x_center  y_center  width  height  confidence  est_box_size
    confidence = 1.0  (hand-picked from 2D classification, fully trusted)
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as fh:
        for x, y in coords:
            fh.write(f"{x:.2f}\t{y:.2f}\t{box_size}\t{box_size}\t1.0\t{box_size}\n")


def write_box(out_path: Path, coords: list[tuple[float, float]], box_size: int) -> None:
    """
    Write an EMAN2 .box file (top-left corner convention).
    Columns: x_corner  y_corner  width  height
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    half = box_size // 2
    with open(out_path, "w") as fh:
        for x, y in coords:
            x_corner = int(round(x)) - half
            y_corner = int(round(y)) - half
            fh.write(f"{x_corner}\t{y_corner}\t{box_size}\t{box_size}\n")


# ---------------------------------------------------------------------------
# format convert
# ---------------------------------------------------------------------------

def convert(star_path: str, output_dir: str, box_size, fmt: str,
            flip_y: bool, mic_height: int) -> None:

    print(f"Reading STAR file: {star_path}")
    particles = parse_star(star_path)
    validate_columns(particles)

    # Attempt auto box-size from star file
    if box_size == "auto":
        if "_rlnImageSize" in particles[0]:
            box_size = int(float(particles[0]["_rlnImageSize"]))
            print(f"  Auto-detected box size from _rlnImageSize: {box_size} px")
        else:
            box_size = 256
            print("  _rlnImageSize not found; set default box size 256 px")
    else:
        box_size = int(box_size)

    # Group particles by micrograph
    by_mic: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for p in particles:
        mic = p["_rlnMicrographName"]
        x = float(p["_rlnCoordinateX"])
        y = float(p["_rlnCoordinateY"])

        # Optional Y-axis flip (needed when RELION and cryOLO conventions differ)
        if flip_y:
            if mic_height <= 0:
                sys.exit("ERROR: --flip-y requires --mic-height > 0")
            y = mic_height - y

        by_mic[mic].append((x, y))

    print(f"  Found {len(particles):,} particles across {len(by_mic):,} micrographs")

    out_root = Path(output_dir)
    ext = ".cbox" if fmt == "cbox" else ".box"
    writer = write_cbox if fmt == "cbox" else write_box

    written = 0
    for mic_path, coords in sorted(by_mic.items()):
        stem = micrograph_basename(mic_path)
        out_file = out_root / (stem + ext)
        writer(out_file, coords, box_size)
        written += 1

    print(f"  Written {written} {ext} files → {out_root}/")
    print("Done.")


# ---------------------------------------------------------------------------
# main function
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert RELION selected particles.star from 2D classification to cryOLO training particle format .cbox or .box",
        epilog="Author: Morgan\n",
    )
    parser.add_argument("star_file",
                        help="Input particles.star (from RELION Select/Class2D job)")
    parser.add_argument("output_dir",
                        help="Directory to write per-micrograph annotation files")
    parser.add_argument("--box-size", default=256,
                        help="Particle box size in pixels. Use 'auto' to read from "
                             "_rlnImageSize in the star file. (default: 256)")
    parser.add_argument("--format", choices=["cbox", "box"], default="cbox",
                        help="Output format: 'cbox' (cryOLO ≥1.7, default) or "
                             "'box' (EMAN2, cryOLO <1.7)")
    parser.add_argument("--flip-y", action="store_true",
                        help="Flip Y coordinates (top-left ↔ bottom-left origin). "
                             "Requires --mic-height.")
    parser.add_argument("--mic-height", type=int, default=0,
                        help="Micrograph height in pixels (required with --flip-y)")

    args = parser.parse_args()

    if not os.path.isfile(args.star_file):
        sys.exit(f"ERROR: STAR file not found: {args.star_file}")

    convert(
        star_path=args.star_file,
        output_dir=args.output_dir,
        box_size=args.box_size,
        fmt=args.format,
        flip_y=args.flip_y,
        mic_height=args.mic_height,
    )


if __name__ == "__main__":
    main()
