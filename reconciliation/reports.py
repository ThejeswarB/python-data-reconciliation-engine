"""Excel report generation with readable formatting."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .engine import ReconciliationResult


def _summary_value(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_excel_report(
    result: ReconciliationResult,
    output_path: str | Path,
) -> Path:
    """Write a formatted multi-sheet Excel workbook for a reconciliation run."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    summary = pd.DataFrame(
        [
            {"Metric": metric.replace("_", " ").title(), "Value": _summary_value(value)}
            for metric, value in result.summary.items()
        ]
    )
    sheets = {
        "Summary": summary,
        "Matched": result.matched,
        "Mismatched": result.mismatched,
        "Mismatch Details": result.mismatch_details,
        "Source Only": result.source_only,
        "Target Only": result.target_only,
        "Source Duplicates": result.source_duplicates,
        "Target Duplicates": result.target_duplicates,
    }

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)

        workbook = writer.book
        header_fill = PatternFill("solid", fgColor="1F4E78")
        header_font = Font(name="Aptos", color="FFFFFF", bold=True)
        source_fill = PatternFill("solid", fgColor="FCE4D6")
        target_fill = PatternFill("solid", fgColor="FFF2CC")

        for worksheet in workbook.worksheets:
            worksheet.sheet_view.showGridLines = False
            worksheet.freeze_panes = "A2"
            worksheet.row_dimensions[1].height = 24

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            if worksheet.max_row > 1 and worksheet.max_column > 0:
                worksheet.auto_filter.ref = worksheet.dimensions

            # Estimate widths from headers and a bounded sample of data rows.
            for column_cells in worksheet.iter_cols():
                column_index = column_cells[0].column
                sample_values = [
                    str(cell.value) if cell.value is not None else ""
                    for cell in column_cells[: min(len(column_cells), 301)]
                ]
                max_length = max((len(value) for value in sample_values), default=10)
                worksheet.column_dimensions[get_column_letter(column_index)].width = min(
                    max(max_length + 2, 12), 42
                )

            if worksheet.title == "Mismatch Details":
                header_positions = {
                    cell.value: cell.column for cell in worksheet[1]
                }
                source_col = header_positions.get("source_value")
                target_col = header_positions.get("target_value")
                for row in range(2, worksheet.max_row + 1):
                    if source_col:
                        worksheet.cell(row, source_col).fill = source_fill
                    if target_col:
                        worksheet.cell(row, target_col).fill = target_fill

            if worksheet.title == "Summary":
                for row in range(2, worksheet.max_row + 1):
                    worksheet.cell(row, 1).font = Font(bold=True, color="1F1F1F")
                    worksheet.cell(row, 2).alignment = Alignment(vertical="top", wrap_text=True)

    return path
