# Environment & Required Dependencies

To dramatically reduce agent token costs and setup time, environment setup has been automated.

### Setup Instructions

Run the setup script from the root of the skill folder:

```bash
chmod +x ./setup.sh
./setup.sh
```

**What it installs:**
- `pandoc` (Extract text from .docx)
- `python3` (Required for `scripts/build_ledger.py` — career ledger scaffolding)
- `node` & `npm` (Required for generation)
- `docx` (npm package for resume generation)
- `libreoffice` (Convert .docx → PDF for page verification)
- `poppler` / `pdfinfo` (Check PDF page count)

If any command fails, install the missing dependency before proceeding.

**Important docx-js notes:**
- NEVER use unicode bullet characters — always use `LevelFormat.BULLET` with numbering config
- US Letter page size: width 12240, height 15840 DXA
- NEVER use `TabStopPosition.MAX` — it defaults to A4. Use explicit `position: 10800` for US Letter with 0.5" margins
