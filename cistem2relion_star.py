# -*- coding: utf-8 -*-
"""
Created on Fri May 22 13:09:00 2026

@author: Aimin Cheng
"""

"""
cistem2relion_star.py

definition: original.star - cisTEM input particle file
            query.star    - selected particle of good class from cisTEM classification,
                            which is converted to star by cisTEM.
                            
mapping: trace particles in query.star back to original.star by matching on
         _rlnDefocusU, _rlnDefocusV, and _rlnPhaseShift (exact string match
         after normalising whitespace).

output: The output STAR file preserves the original.star optics block and
        header structure, and each matched particle row is pulled from
        original.star so that all 20 parameters are restored.

Usage:
    python cistem2relion_star.py \
        --original original.star \
        --query    query.star \
        --output   restored.star

Optional flags:
    --tolerance  Float tolerance for numeric matching (default: exact
                 string match after normalisation).  Set e.g. 0.001
                 to allow small floating-point differences.
    --unmatched  Path to write query particles that had no match (for
                 QC; omit to skip).
    --ambiguous  Path to write a STAR file containing the 2nd, 3rd, …
                 candidates from original.star whenever a query key
                 matched more than one original row.  The file uses the
                 same header as original.star.
"""

#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# particle star file parser
# ---------------------------------------------------------------------------

def parse_star(path: Path):
    """
    Parse a RELION STAR file.

    Returns a list of blocks, each block is a dict:
        {
            'name':    str,               # e.g. 'optics', 'particles'
            'columns': list[str],         # column labels in order
            'rows':    list[list[str]],   # raw string values per row
            'raw_header_lines': list[str] # the loop_ + _rln... lines verbatim
        }

    Lines outside data_ blocks (version comments etc.) are also captured
    as 'preamble' entries with name='_preamble' and no columns/rows.
    """
    text = path.read_bytes().decode('utf-8', errors='replace')
    lines = text.splitlines()

    blocks = []
    preamble_lines = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # --- data block header ------------------------------------------
        if line.startswith('data_'):
            block_name = line[5:]  # everything after 'data_'

            # flush preamble if any
            if preamble_lines:
                blocks.append({
                    'name': '_preamble',
                    'preamble': list(preamble_lines),
                    'columns': [],
                    'rows': [],
                    'raw_header_lines': [],
                })
                preamble_lines = []

            i += 1
            block = {
                'name': block_name,
                'columns': [],
                'rows': [],
                'raw_header_lines': [],
                'pre_loop_lines': [],  # blank lines between data_ and loop_
            }

            # skip blank lines before loop_
            while i < len(lines) and lines[i].strip() == '':
                block['pre_loop_lines'].append(lines[i])
                i += 1

            # expect loop_
            if i < len(lines) and lines[i].strip() == 'loop_':
                block['raw_header_lines'].append(lines[i])
                i += 1
            else:
                # no loop_ — empty or malformed block
                blocks.append(block)
                continue

            # read column definitions (_rln... #N)
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped.startswith('_rln'):
                    col_name = stripped.split()[0]
                    block['columns'].append(col_name)
                    block['raw_header_lines'].append(lines[i])
                    i += 1
                else:
                    break

            # read data rows until next blank-then-data_ or EOF
            while i < len(lines):
                raw = lines[i]
                stripped = raw.strip()
                if stripped == '' or stripped.startswith('data_') or stripped.startswith('#'):
                    break
                if stripped:
                    block['rows'].append(stripped.split())
                i += 1

            blocks.append(block)
            continue

        # --- version / comment lines and blank lines outside blocks -------
        preamble_lines.append(lines[i])
        i += 1

    # flush trailing preamble
    if preamble_lines:
        blocks.append({
            'name': '_preamble',
            'preamble': list(preamble_lines),
            'columns': [],
            'rows': [],
            'raw_header_lines': [],
        })

    return blocks


# ---------------------------------------------------------------------------
# checking
# ---------------------------------------------------------------------------

def get_col_index(block, name):
    """Return 0-based index of column `name` in block, or raise KeyError."""
    try:
        return block['columns'].index(name)
    except ValueError:
        raise KeyError(f"Column '{name}' not found in data_{block['name']} block. "
                       f"Available: {block['columns']}")


def normalise_float(s: str) -> str:
    """
    Normalise a numeric string for exact comparison:
    convert to float then back to a canonical string so that
    '16143.426758' and '16143.426758' compare equal regardless of
    leading/trailing whitespace or differing zero-padding.
    Falls back to the raw stripped string if not parseable.
    """
    try:
        return repr(float(s))
    except ValueError:
        return s.strip()


def make_key(row, idx_u, idx_v, idx_ps, tolerance=None):
    """
    Build a lookup key tuple from (DefocusU, DefocusV, PhaseShift).

    With tolerance=None  → exact normalised string match.
    With tolerance=float → round each value to nearest multiple of
                           tolerance for bucketing (simple approach).
    """
    if tolerance is None:
        return (
            normalise_float(row[idx_u]),
            normalise_float(row[idx_v]),
            normalise_float(row[idx_ps]),
        )
    else:
        def bucket(s):
            v = float(s)
            return round(v / tolerance)
        return (bucket(row[idx_u]), bucket(row[idx_v]), bucket(row[idx_ps]))


# ---------------------------------------------------------------------------
# star file writing
# ---------------------------------------------------------------------------

def write_star(out_path: Path, orig_blocks, matched_rows, orig_particles_block):
    """
    Write output STAR reproducing original.star's optics header and
    particles block header, but with only the matched rows.
    """
    lines = []

    for block in orig_blocks:
        if block['name'] == '_preamble':
            lines.extend(block.get('preamble', []))
            continue

        # data_ line
        lines.append(f'data_{block["name"]}')
        lines.append('')

        # loop_ and column headers
        for h in block['raw_header_lines']:
            lines.append(h.rstrip('\r\n'))

        if block['name'] == 'particles':
            # write matched rows (verbatim original whitespace-normalised)
            for row in matched_rows:
                lines.append(' '.join(row))
        else:
            # optics and any other blocks: copy rows as-is
            for row in block['rows']:
                lines.append(' '.join(row))

        lines.append('')
        lines.append('')

    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='mapping full particle parameters from cisTEM input particle original.star '
                    'by matching DefocusU / DefocusV / PhaseShift parameters in cisTEM classification output particle query.star.')
    parser.add_argument('--original', required=True, help='Path to original.star input into cisTEM processing')
    parser.add_argument('--query',    required=True, help='Path to query.star output from cisTEM classification')
    parser.add_argument('--output',   required=True, help='Path for output restored.star after particle mapping')
    parser.add_argument('--tolerance', type=float, default=None,
                        help='Numeric tolerance for matching (default: exact). '
                             'E.g. 0.001 allows ±0.001 difference.')
    parser.add_argument('--unmatched', default=None,
                        help='Optional path to write unmatched query rows for QC.')
    parser.add_argument('--ambiguous', default=None,
                        help='Optional path to write a STAR file containing the '
                             '2nd, 3rd, … original.star candidates whenever a '
                             'query key matched more than one row.')
    args = parser.parse_args()

    original_path = Path(args.original)
    query_path    = Path(args.query)
    output_path   = Path(args.output)

    print(f'Reading original : {original_path}')
    orig_blocks = parse_star(original_path)

    print(f'Reading query    : {query_path}')
    qry_blocks  = parse_star(query_path)

    # --- locate particles blocks -----------------------------------------
    orig_particles = next((b for b in orig_blocks if b['name'] == 'particles'), None)
    qry_particles  = next((b for b in qry_blocks  if b['name'] == 'particles'), None)

    if orig_particles is None:
        sys.exit('ERROR: data_particles block not found in original.star')
    if qry_particles is None:
        sys.exit('ERROR: data_particles block not found in query.star')

    # --- column indices in original ---------------------------------------
    try:
        oi_u  = get_col_index(orig_particles, '_rlnDefocusU')
        oi_v  = get_col_index(orig_particles, '_rlnDefocusV')
        oi_ps = get_col_index(orig_particles, '_rlnPhaseShift')
    except KeyError as e:
        sys.exit(f'ERROR in original.star: {e}')

    # --- column indices in query -----------------------------------------
    try:
        qi_u  = get_col_index(qry_particles, '_rlnDefocusU')
        qi_v  = get_col_index(qry_particles, '_rlnDefocusV')
        qi_ps = get_col_index(qry_particles, '_rlnPhaseShift')
    except KeyError as e:
        sys.exit(f'ERROR in query.star: {e}')

    # --- build lookup from original --------------------------------------
    print(f'Original particles : {len(orig_particles["rows"])}')
    print(f'Query particles    : {len(qry_particles["rows"])}')

    tol = args.tolerance
    orig_lookup = {}  # key -> list of original rows (handle duplicates)
    for row in orig_particles['rows']:
        k = make_key(row, oi_u, oi_v, oi_ps, tol)
        orig_lookup.setdefault(k, []).append(row)

    n_dup_keys = sum(1 for v in orig_lookup.values() if len(v) > 1)
    if n_dup_keys:
        print(f'  NOTE: {n_dup_keys} key(s) in original.star have >1 row — '
              f'extra candidates will be written to the ambiguous output file.')

    # --- match query rows to original ------------------------------------
    matched_rows   = []   # first-match rows → main output
    ambiguous_rows = []   # 2nd, 3rd, … candidates → ambiguous output
    unmatched      = []   # query rows with no match at all

    for qrow in qry_particles['rows']:
        k = make_key(qrow, qi_u, qi_v, qi_ps, tol)
        candidates = orig_lookup.get(k)
        if candidates is None:
            unmatched.append(qrow)
        else:
            matched_rows.append(candidates[0])       # best (first) match
            if len(candidates) > 1:
                ambiguous_rows.extend(candidates[1:])  # overflow candidates

    print(f'Matched            : {len(matched_rows)}')
    print(f'Ambiguous extras   : {len(ambiguous_rows)}')
    print(f'Unmatched          : {len(unmatched)}')

    # --- write primary output --------------------------------------------
    write_star(output_path, orig_blocks, matched_rows, orig_particles)
    print(f'Written            : {output_path}')

    # --- write ambiguous candidates --------------------------------------
    if ambiguous_rows:
        if args.ambiguous:
            ambiguous_path = Path(args.ambiguous)
        else:
            # auto-generate a sibling path next to the output file
            ambiguous_path = output_path.with_name(
                output_path.stem + '_ambiguous' + output_path.suffix
            )
        write_star(ambiguous_path, orig_blocks, ambiguous_rows, orig_particles)
        print(f'Ambiguous written  : {ambiguous_path}  '
              f'({len(ambiguous_rows)} row(s))')
        print('  These are the 2nd, 3rd, … original.star rows that shared the')
        print('  same (DefocusU, DefocusV, PhaseShift) key as a query particle.')
        print('  Inspect them to decide which match is correct.')

    # --- optionally dump unmatched rows ----------------------------------
    if args.unmatched and unmatched:
        unmatched_path = Path(args.unmatched)
        with unmatched_path.open('w', encoding='utf-8') as f:
            f.write('\t'.join(qry_particles['columns']) + '\n')
            for row in unmatched:
                f.write('\t'.join(row) + '\n')
        print(f'Unmatched rows     : {unmatched_path}')

    if unmatched:
        print('\nWARNING: some query particles had no match in original.star.')
        print('  Possible causes:')
        print('  - Floating-point rounding differs between files')
        print('    → try --tolerance 0.001')
        print('  - The particle genuinely is not in original.star')
        sys.exit(1)


if __name__ == '__main__':
    main()
