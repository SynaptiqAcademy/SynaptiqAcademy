"""Statistical Intelligence 2.0 — Data parser (Phase X).

Parses text (statistical results), CSV, Excel, JSON, SPSS, Stata, R datasets.
Heavy-dependency parsers (openpyxl, pyreadstat) are deferred imports — missing
packages gracefully fall back to raw text extraction.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
from pathlib import Path
from typing import Any

from .models import ColumnInfo, InputFormat, ParsedData

log = logging.getLogger("synaptiq.statistical.parser")

MAX_CONTENT_CHARS = 80_000
MIN_CONTENT_CHARS = 20


# ── Format detection ──────────────────────────────────────────────────────────

_MIME_MAP: dict[str, InputFormat] = {
    "text/csv": InputFormat.CSV,
    "application/csv": InputFormat.CSV,
    "text/plain": InputFormat.TEXT,
    "application/json": InputFormat.JSON,
    "text/json": InputFormat.JSON,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": InputFormat.EXCEL,
    "application/vnd.ms-excel": InputFormat.EXCEL,
    "application/x-spss-sav": InputFormat.SPSS,
    "application/x-stata-dta": InputFormat.STATA,
}

_EXT_MAP: dict[str, InputFormat] = {
    ".csv": InputFormat.CSV,
    ".tsv": InputFormat.CSV,
    ".xlsx": InputFormat.EXCEL,
    ".xls": InputFormat.EXCEL,
    ".json": InputFormat.JSON,
    ".sav": InputFormat.SPSS,
    ".dta": InputFormat.STATA,
    ".rda": InputFormat.R_DATASET,
    ".rds": InputFormat.R_DATASET,
    ".txt": InputFormat.TEXT,
}


def detect_format(filename: str, mime: str = "") -> InputFormat:
    if mime in _MIME_MAP:
        return _MIME_MAP[mime]
    ext = Path(filename).suffix.lower()
    return _EXT_MAP.get(ext, InputFormat.TEXT)


# ── CSV / TSV ─────────────────────────────────────────────────────────────────

def parse_csv(data: bytes | str, sep: str = "") -> ParsedData:
    text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
    # Auto-detect separator
    if not sep:
        sep = "," if text.count(",") >= text.count("\t") else "\t"

    reader = csv.DictReader(io.StringIO(text), delimiter=sep)
    rows: list[dict] = []
    try:
        rows = [row for row in reader]
    except Exception:
        pass

    columns: list[ColumnInfo] = []
    if rows and reader.fieldnames:
        for fname in reader.fieldnames:
            values = [r.get(fname, "") for r in rows]
            missing = sum(1 for v in values if v is None or v == "")
            numeric_vals: list[float] = []
            for v in values:
                try:
                    numeric_vals.append(float(v))
                except (TypeError, ValueError):
                    pass
            is_num = len(numeric_vals) >= len(values) * 0.7
            col = ColumnInfo(
                name=str(fname),
                dtype="numeric" if is_num else "categorical",
                missing_count=missing,
                missing_rate=missing / max(len(rows), 1),
                unique_count=len(set(values)),
                is_numeric=is_num,
                is_binary=len(set(values)) == 2,
            )
            if is_num and numeric_vals:
                import statistics
                col.min_val = min(numeric_vals)
                col.max_val = max(numeric_vals)
                col.mean_val = statistics.mean(numeric_vals)
                col.std_val = statistics.stdev(numeric_vals) if len(numeric_vals) > 1 else 0.0
            columns.append(col)

    numeric_cols = [c.name for c in columns if c.is_numeric]
    cat_cols = [c.name for c in columns if not c.is_numeric]
    binary_cols = [c.name for c in columns if c.is_binary]
    overall_missing = (
        sum(c.missing_count for c in columns) / max(len(columns) * len(rows), 1)
        if columns and rows else 0.0
    )

    doc = ParsedData(
        raw_text=text[:MAX_CONTENT_CHARS],
        input_format=InputFormat.CSV,
        has_structured_data=bool(rows),
        columns=columns,
        row_count=len(rows),
        sample_size=len(rows),
        numeric_columns=numeric_cols,
        categorical_columns=cat_cols,
        binary_columns=binary_cols,
        overall_missing_rate=overall_missing,
    )
    return doc


# ── Excel ─────────────────────────────────────────────────────────────────────

def parse_excel(data: bytes) -> ParsedData:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        rows_raw = list(ws.iter_rows(values_only=True))
        if not rows_raw:
            return ParsedData(raw_text="[Empty Excel file]", input_format=InputFormat.EXCEL)
        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows_raw[0])]
        data_rows = rows_raw[1:]
        # Convert to CSV-like text for enrichment
        csv_lines = [",".join(headers)]
        for row in data_rows:
            csv_lines.append(",".join(str(c) if c is not None else "" for c in row))
        csv_text = "\n".join(csv_lines)
        doc = parse_csv(csv_text.encode())
        doc.input_format = InputFormat.EXCEL
        return doc
    except ImportError:
        log.warning("openpyxl not available; treating Excel as text")
        return ParsedData(
            raw_text=f"[Excel file — {len(data)} bytes — openpyxl not installed]",
            input_format=InputFormat.EXCEL,
        )
    except Exception as exc:
        log.warning("Excel parse error: %s", exc)
        return ParsedData(raw_text=f"[Excel parse error: {exc}]", input_format=InputFormat.EXCEL)


# ── JSON ──────────────────────────────────────────────────────────────────────

def parse_json(data: bytes | str) -> ParsedData:
    text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return ParsedData(raw_text=text[:MAX_CONTENT_CHARS], input_format=InputFormat.JSON)

    # Try to detect a flat list-of-dicts (tabular JSON)
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        csv_io = io.StringIO()
        writer = csv.DictWriter(csv_io, fieldnames=list(obj[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(obj)
        doc = parse_csv(csv_io.getvalue().encode())
        doc.input_format = InputFormat.JSON
        return doc

    # Nested JSON → flatten to text
    flat_text = json.dumps(obj, indent=2)
    return ParsedData(
        raw_text=flat_text[:MAX_CONTENT_CHARS],
        input_format=InputFormat.JSON,
        has_structured_data=True,
        metadata={"json_type": type(obj).__name__},
    )


# ── SPSS ──────────────────────────────────────────────────────────────────────

def parse_spss(data: bytes) -> ParsedData:
    try:
        import pyreadstat
        df, meta = pyreadstat.read_sav(io.BytesIO(data))
        csv_text = df.to_csv(index=False)
        doc = parse_csv(csv_text.encode())
        doc.input_format = InputFormat.SPSS
        doc.metadata["variable_labels"] = meta.column_labels or []
        return doc
    except ImportError:
        return ParsedData(
            raw_text=f"[SPSS file — {len(data)} bytes — pyreadstat not installed]",
            input_format=InputFormat.SPSS,
        )
    except Exception as exc:
        log.warning("SPSS parse error: %s", exc)
        return ParsedData(raw_text=f"[SPSS parse error: {exc}]", input_format=InputFormat.SPSS)


# ── Stata ─────────────────────────────────────────────────────────────────────

def parse_stata(data: bytes) -> ParsedData:
    try:
        import pyreadstat
        df, meta = pyreadstat.read_dta(io.BytesIO(data))
        csv_text = df.to_csv(index=False)
        doc = parse_csv(csv_text.encode())
        doc.input_format = InputFormat.STATA
        return doc
    except ImportError:
        return ParsedData(
            raw_text=f"[Stata file — {len(data)} bytes — pyreadstat not installed]",
            input_format=InputFormat.STATA,
        )
    except Exception as exc:
        return ParsedData(raw_text=f"[Stata parse error: {exc}]", input_format=InputFormat.STATA)


# ── Plain text (statistical output paste) ─────────────────────────────────────

_SAMPLE_SIZE_RE = re.compile(r"\b[Nn]\s*[=:]\s*([\d,]+)")
_P_VALUE_RE = re.compile(r"\bp\s*[=<>]\s*[0-9.]+")


def parse_text(text: str) -> ParsedData:
    cleaned = re.sub(r"\n{4,}", "\n\n\n", text).strip()[:MAX_CONTENT_CHARS]
    # Attempt to auto-detect sample size from text
    n_match = _SAMPLE_SIZE_RE.search(cleaned)
    sample_size = 0
    if n_match:
        try:
            sample_size = int(n_match.group(1).replace(",", ""))
        except ValueError:
            pass

    return ParsedData(
        raw_text=cleaned,
        input_format=InputFormat.TEXT,
        has_structured_data=False,
        sample_size=sample_size,
        word_count=len(cleaned.split()),
    )


# ── Dispatcher ────────────────────────────────────────────────────────────────

def parse_input(data: bytes | str, fmt: InputFormat) -> ParsedData:
    if fmt == InputFormat.CSV:
        return parse_csv(data if isinstance(data, bytes) else data.encode())
    if fmt == InputFormat.EXCEL:
        return parse_excel(data if isinstance(data, bytes) else data.encode())
    if fmt == InputFormat.JSON:
        return parse_json(data)
    if fmt == InputFormat.SPSS:
        return parse_spss(data if isinstance(data, bytes) else data.encode())
    if fmt == InputFormat.STATA:
        return parse_stata(data if isinstance(data, bytes) else data.encode())
    text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
    return parse_text(text)
