#!/usr/bin/env python3
"""One-time script to create the test Excel fixture."""
import os
from openpyxl import Workbook

os.makedirs("tests/fixtures", exist_ok=True)
wb = Workbook()
ws = wb.active
ws.append(["Company Name", "Job Description", "Summary"])
ws.append(["TestCorp", "We need a Data Analyst with SQL, Python, and Tableau experience. 2+ years required.", ""])
ws.append(["TestCorp", "Looking for a Risk Analyst with strong SQL and Excel skills.", ""])
ws.append(["Acme Inc", "Hiring a Business Intelligence Analyst. Must know BigQuery, Looker, and dbt.", ""])
wb.save("tests/fixtures/sample_batch.xlsx")
print("Created tests/fixtures/sample_batch.xlsx")
