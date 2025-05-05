#!/usr/bin/env python3
"""
parse_excel_to_json.py
---------------------

Convert a multi‑sheet Excel workbook to JSON, preserving the layout used
in the "BOMAG comparison" file.

JSON layout produced
====================
{
  "<Sheet‑Name>": {
    "<Machine‑Name>": {
      "<Attribute‑1>": <value>,
      "<Attribute‑2>": <value>,
      ...
      "Tiempo": {               # ← LTR‑only (if present)
        "<Tiempo‑key‑1>": <value>,
        "<Tiempo‑key‑2>": <value>,
        ...
      }
    },
    ...
  },
  ...
}

Usage
=====
# Single consolidated JSON file
$ python parse_excel_to_json.py "Bomag-comparison.xlsx" \
      --out comparison.json

# One JSON file per sheet
$ python parse_excel_to_json.py "Bomag-comparison.xlsx" \
      --out data/ --split
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Dict, Any

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────
def _is_nan(val: Any) -> bool:
    """True for None, empty string, or NaN."""
    return (
        val is None
        or (isinstance(val, float) and math.isnan(val))
        or (isinstance(val, str) and val.strip() == "")
    )


def _coerce_number(val: Any) -> Any:
    """Convert float→int when the value is whole; leave everything else intact."""
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val


# ─────────────────────────────────────────────────────────────────────────────
# Core parsing functions
# ─────────────────────────────────────────────────────────────────────────────
def sheet_to_records(df: pd.DataFrame, sheet_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Convert a single sheet into {machine: {attribute: value}}.

    Special handling:
      • For sheet 'LTR', rows from the cell containing "Tiempo" downward
        (until a blank / new header) are grouped under a 'Tiempo' sub‑dict
        for each machine.
    """
    # 1️⃣ Locate attribute column (has 'Máquina' or 'Machine')
    attr_col = None
    maquina_row = None
    for col in df.columns:
        mask = df[col].astype(str).str.contains(r"\b(Máquina|Machine)\b",
                                                case=False, na=False)
        if mask.any():
            attr_col = col
            maquina_row = mask.idxmax()
            break
    if attr_col is None:
        raise ValueError(f'No "Máquina/Machine" column found in sheet "{sheet_name}"')

    header_row = maquina_row - 1
    machine_series = df.loc[header_row, attr_col + 1 :].dropna(how="all")
    machine_cols = machine_series.index

    # Sheets other than LTR → simple, flat parsing
    if sheet_name.upper() != "LTR":
        return _flat_records(df, attr_col, maquina_row, machine_series, sheet_name)

    # 2️⃣ LTR‑specific logic — detect Tiempo block
    tiempo_start, tiempo_end = _find_tiempo_block(df, attr_col, maquina_row)

    sheet_dict: Dict[str, Dict[str, Any]] = {}
    for mcol in machine_cols:
        mname = str(machine_series[mcol]).strip()
        if not mname or mname.lower() == "nan":
            continue

        record: Dict[str, Any] = {}
        tiempo_dict: Dict[str, Any] = {}

        for idx in range(maquina_row, len(df)):
            attr = df.loc[idx, attr_col]
            if _is_nan(attr):
                continue
            attr = str(attr).strip()

            val = df.loc[idx, mcol]
            if _is_nan(val):
                continue
            val = _coerce_number(val)

            in_tiempo = (
                tiempo_start is not None
                and tiempo_start <= idx < tiempo_end
            )
            if in_tiempo:
                tiempo_dict[attr] = val
            else:
                record[attr] = val

        if tiempo_dict:
            record["Tiempo"] = tiempo_dict
        sheet_dict[mname] = record

    return sheet_dict


def _find_tiempo_block(df: pd.DataFrame, attr_col: int, start_row: int) -> tuple[int | None, int]:
    """Return (start_idx, end_idx) of the Tiempo block in LTR, else (None, None)."""
    tiempo_start = None
    for idx in range(start_row, len(df)):
        cell = str(df.loc[idx, attr_col]).strip().lower()
        if cell == "tiempo":
            tiempo_start = idx
            break

    if tiempo_start is None:
        return None, None

    # Tiempo block ends at first empty attr or new header row
    tiempo_end = len(df)
    for idx in range(tiempo_start + 1, len(df)):
        nxt = str(df.loc[idx, attr_col]).strip().lower()
        if nxt in {"", "nan", "máquina", "machine"}:
            tiempo_end = idx
            break
    return tiempo_start, tiempo_end


def _flat_records(
    df: pd.DataFrame,
    attr_col: int,
    maquina_row: int,
    machine_series: pd.Series,
    sheet_name: str
) -> Dict[str, Dict[str, Any]]:
    """Default parser for sheets without special sections."""
    machine_cols = machine_series.index
    out: Dict[str, Dict[str, Any]] = {}
    
    # For SDR tab, we'll group machines by brand
    if sheet_name == "SDR":
        brand_machines: Dict[str, list] = {}
        for mcol in machine_cols:
            mname = str(machine_series[mcol]).strip()
            if not mname:
                continue
                
            # Extract brand and model
            parts = mname.split(' ', 1)
            if len(parts) == 2:
                brand, model = parts
            else:
                brand = mname
                model = mname
                
            rec: Dict[str, Any] = {}
            for idx in range(maquina_row, len(df)):
                attr = df.loc[idx, attr_col]
                if _is_nan(attr):
                    continue
                val = df.loc[idx, mcol]
                if _is_nan(val):
                    continue
                rec[str(attr).strip()] = _coerce_number(val)
                
            if brand not in brand_machines:
                brand_machines[brand] = []
            brand_machines[brand].append(rec)
            
        # Convert the brand_machines dictionary to the expected format
        for brand, machines in brand_machines.items():
            out[brand] = machines
    else:
        # For other tabs, keep the original behavior
        for mcol in machine_cols:
            mname = str(machine_series[mcol]).strip()
            if not mname:
                continue
            rec: Dict[str, Any] = {}
            for idx in range(maquina_row, len(df)):
                attr = df.loc[idx, attr_col]
                if _is_nan(attr):
                    continue
                val = df.loc[idx, mcol]
                if _is_nan(val):
                    continue
                rec[str(attr).strip()] = _coerce_number(val)
            out[mname] = rec
            
    return out


def workbook_to_json(path: Path) -> Dict[str, Dict[str, Any]]:
    """Parse every sheet in *path* into the nested JSON structure."""
    xls = pd.ExcelFile(path)
    book_dict: Dict[str, Dict[str, Any]] = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet, header=None)
        book_dict[sheet] = sheet_to_records(df, sheet)
    return book_dict


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Excel → JSON parser (BOMAG style)")
    ap.add_argument("excel", type=Path, help="Path to .xlsx file")
    ap.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output .json file OR directory when --split is set",
    )
    ap.add_argument(
        "--split",
        action="store_true",
        help="Write one JSON file per sheet into --out directory",
    )
    args = ap.parse_args()

    data = workbook_to_json(args.excel)

    if args.split:
        args.out.mkdir(parents=True, exist_ok=True)
        for sheet, content in data.items():
            out_file = args.out / f"{sheet}.json"
            out_file.write_text(json.dumps(content, indent=2, ensure_ascii=False))
            print(f"✔︎ wrote {out_file}")
    else:
        args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"✔︎ wrote {args.out}")


if __name__ == "__main__":
    main()
