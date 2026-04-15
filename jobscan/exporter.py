"""Export jobs to batch_jds_auto.xlsx for the tailoring pipeline."""
from __future__ import annotations

import openpyxl

HEADERS = ["company", "Job Description Text", "url", "location"]


def export_to_xlsx(jobs: list[dict], output_path: str) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADERS)

    for job in jobs:
        ws.append([
            job.get("company", ""),
            job.get("description", ""),
            job.get("url", ""),
            job.get("location", ""),
        ])

    wb.save(output_path)
    return output_path
