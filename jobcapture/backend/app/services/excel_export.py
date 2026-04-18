import io
import re
import openpyxl

HEADERS = ["company", "Job Description Text", "company_url", "url", "location"]

# Characters openpyxl rejects in worksheet cells (XML-illegal control chars).
_ILLEGAL_XLSX_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

def _clean(value: str) -> str:
    return _ILLEGAL_XLSX_CHARS.sub("", value or "")

def generate_batch_xlsx(jobs: list[dict]) -> io.BytesIO:
    """Generate batch_jds.xlsx matching the existing format.
    Each dict must have: company, description, url, company_url, location.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADERS)

    for job in jobs:
        ws.append([
            _clean(job.get("company", "")),
            _clean(job.get("description", "")),
            _clean(job.get("company_url", "")),
            _clean(job.get("url", "")),
            _clean(job.get("location", "")),
        ])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
