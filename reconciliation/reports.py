"""Excel report generation with readable formatting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .engine import ReconciliationResult


def write_excel_report(
    result: ReconciliationResult,
    output_path: str | Path,
) -> Path:
    """Write a formatted multi-sheet Excel workbook for a reconciliation run."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    sheets = {
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
        summary_ws = workbook.create_sheet("Summary", 0)

        # Build the summary as two small, readable tables rather than serializing
        # Python lists/dictionaries into single Excel cells.
        title_fill = PatternFill("solid", fgColor="17365D")
        section_fill = PatternFill("solid", fgColor="D9EAF7")
        header_fill = PatternFill("solid", fgColor="1F4E78")
        header_font = Font(name="Aptos", color="FFFFFF", bold=True)
        source_fill = PatternFill("solid", fgColor="FCE4D6")
        target_fill = PatternFill("solid", fgColor="FFF2CC")
        thin_blue_font = Font(name="Aptos", color="1F1F1F", bold=True)

        summary_ws.sheet_view.showGridLines = False
        summary_ws.merge_cells("A1:B1")
        summary_ws["A1"] = "Reconciliation Report"
        summary_ws["A1"].fill = title_fill
        summary_ws["A1"].font = Font(name="Aptos Display", size=16, bold=True, color="FFFFFF")
        summary_ws["A1"].alignment = Alignment(vertical="center")
        summary_ws.row_dimensions[1].height = 32

        summary_ws.merge_cells("A3:B3")
        summary_ws["A3"] = "Reconciliation Metrics"
        summary_ws["A3"].fill = section_fill
        summary_ws["A3"].font = Font(name="Aptos", bold=True, color="17365D")
        summary_ws.row_dimensions[3].height = 22

        summary_ws.append([])  # Preserve the intentional section spacing.
        summary_ws["A4"] = "Metric"
        summary_ws["B4"] = "Value"

        metric_labels = {
            "source_records": "Source Records",
            "target_records": "Target Records",
            "matched_records": "Matched Records",
            "mismatched_records": "Mismatched Records",
            "source_only_records": "Source-only Records",
            "target_only_records": "Target-only Records",
            "source_duplicate_records": "Source Duplicate Records",
            "target_duplicate_records": "Target Duplicate Records",
            "mismatch_detail_rows": "Field-level Mismatch Details",
        }
        metric_row = 5
        for key, label in metric_labels.items():
            if key in result.summary:
                summary_ws.cell(metric_row, 1, label)
                summary_ws.cell(metric_row, 2, result.summary[key])
                summary_ws.cell(metric_row, 1).font = thin_blue_font
                metric_row += 1

        column_section_row = metric_row + 2
        summary_ws.merge_cells(
            start_row=column_section_row, start_column=1,
            end_row=column_section_row, end_column=2
        )
        section_cell = summary_ws.cell(column_section_row, 1, "Column-level Mismatch Counts")
        section_cell.fill = section_fill
        section_cell.font = Font(name="Aptos", bold=True, color="17365D")
        summary_ws.row_dimensions[column_section_row].height = 22

        column_header_row = column_section_row + 1
        summary_ws.cell(column_header_row, 1, "Comparison Column")
        summary_ws.cell(column_header_row, 2, "Mismatched Records")
        mismatch_counts = result.summary.get("column_mismatch_counts", {})
        if mismatch_counts:
            for row_number, (column, count) in enumerate(mismatch_counts.items(), start=column_header_row + 1):
                summary_ws.cell(row_number, 1, str(column))
                summary_ws.cell(row_number, 2, int(count))
        else:
            summary_ws.cell(column_header_row + 1, 1, "No comparison columns configured")
            summary_ws.cell(column_header_row + 1, 2, 0)

        for header_row in (4, column_header_row):
            for cell in summary_ws[header_row][:2]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            summary_ws.row_dimensions[header_row].height = 22

        for row in summary_ws.iter_rows(min_row=5, max_row=summary_ws.max_row, min_col=1, max_col=2):
            row[1].alignment = Alignment(horizontal="left", vertical="center")
        summary_ws.column_dimensions["A"].width = 34
        summary_ws.column_dimensions["B"].width = 24
        summary_ws.freeze_panes = "A5"

        for sheet_name, worksheet in ((name, workbook[name]) for name in sheets):
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
                header_positions = {cell.value: cell.column for cell in worksheet[1]}
                source_col = header_positions.get("source_value")
                target_col = header_positions.get("target_value")
                for row in range(2, worksheet.max_row + 1):
                    if source_col:
                        worksheet.cell(row, source_col).fill = source_fill
                    if target_col:
                        worksheet.cell(row, target_col).fill = target_fill

    return path
