# Kindle Scribe PDF Optimizer

Always follow these instructions precisely and fallback to search or bash commands only when you encounter unexpected information that does not match what is documented here.

Kindle Scribe PDF Optimizer is a Python application that converts existing PDFs to be more readable on Kindle Scribe devices. It preserves content while optimizing formatting through grayscale conversion, margin cropping, and page resizing. The tool offers both a Tkinter desktop GUI and a Flask web interface.

## Working Effectively

### Initial Setup (Fresh Clone)
Run these commands in order on a fresh repository clone:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**TIMING**: Virtual environment creation takes 4 seconds. Dependencies installation takes 16 seconds. NEVER CANCEL these operations.

**NETWORK DEPENDENCY**: If pip install fails with timeout errors due to network connectivity issues, increase timeout: `.venv/bin/pip install --timeout 180 -r requirements.txt`

### Install Ghostscript (Recommended)
For vector-preserving grayscale conversion, install Ghostscript:

```bash
sudo apt-get update && sudo apt-get install -y ghostscript
```

**TIMING**: Ghostscript installation takes 23 seconds. NEVER CANCEL. Set timeout to 60+ seconds.

If Ghostscript is not available, the tool automatically falls back to a high-quality raster pipeline using PyMuPDF + Pillow.

### Generate Test Data
Always create test PDF before testing changes:

```bash
.venv/bin/python tests/generate_sample_pdf.py
```

**TIMING**: PDF generation takes 0.09 seconds.

### Core Usage Patterns

#### CLI Optimization
```bash
# Basic optimization (Scribe page size, default margins)
.venv/bin/python -m scribe_tools.scribe_optimize input.pdf

# With output path
.venv/bin/python -m scribe_tools.scribe_optimize input.pdf --out output.pdf

# A5 page size
.venv/bin/python -m scribe_tools.scribe_optimize input.pdf --page-size a5

# Force raster mode (bypass Ghostscript)
.venv/bin/python -m scribe_tools.scribe_optimize input.pdf --force-raster
```

**TIMING**: PDF optimization takes 0.3-0.4 seconds per file. NEVER CANCEL operations under 30 seconds.

#### GUI Application (Desktop)
```bash
.venv/bin/python -m scribe_tools.app
```

**Note**: Tkinter is not available in most Linux environments. The launcher automatically detects this and falls back to web UI.

#### Web Interface
```bash
# Test mode (bypass paywall)
export PAYWALL_TEST_MODE=1
export SCRIBE_UI_FORCE_WEB=1
.venv/bin/python -m scribe_tools.app
```

**Alternative using script** (if zsh available):
```bash
./scripts/run_web_test.sh
```

**TIMING**: Web UI starts instantly (under 1 second). Accessible at http://127.0.0.1:PORT where PORT is auto-assigned.

For production mode, see `scripts/run_web_prod.sh` (requires Stripe environment variables).

## Validation Scenarios

### Complete End-to-End Testing
After making any changes, ALWAYS run through this complete validation:

1. **Basic CLI Test**:
```bash
.venv/bin/python tests/generate_sample_pdf.py
.venv/bin/python -m scribe_tools.scribe_optimize tests/sample.pdf --out tests/validation_output.pdf
```
Expected: Creates `tests/validation_output.pdf` (typically 177KB) in 0.3-0.4 seconds.

2. **Web Interface Test**:
```bash
export PAYWALL_TEST_MODE=1
export SCRIBE_UI_FORCE_WEB=1
.venv/bin/python -m scribe_tools.app &
```
Then open browser to http://127.0.0.1:PORT, upload `tests/sample.pdf`, click "Optimize", and verify download works.

3. **Page Size Options Test**:
```bash
.venv/bin/python -m scribe_tools.scribe_optimize tests/sample.pdf --page-size scribe --out tests/scribe_test.pdf
.venv/bin/python -m scribe_tools.scribe_optimize tests/sample.pdf --page-size a5 --out tests/a5_test.pdf
.venv/bin/python -m scribe_tools.scribe_optimize tests/sample.pdf --page-size source --out tests/source_test.pdf
```

4. **Ghostscript vs Raster Test**:
```bash
# Vector mode (if Ghostscript available)
.venv/bin/python -m scribe_tools.scribe_optimize tests/sample.pdf --out tests/vector_test.pdf

# Raster mode (fallback)
.venv/bin/python -m scribe_tools.scribe_optimize tests/sample.pdf --force-raster --out tests/raster_test.pdf
```

## Timeout Guidelines and Critical Warnings

- **NEVER CANCEL**: Any operation under 30 seconds
- **Dependencies installation**: Set timeout to 60+ seconds (takes 16 seconds)
- **Ghostscript installation**: Set timeout to 60+ seconds (takes 23 seconds)
- **PDF processing**: Set timeout to 30+ seconds (takes 0.3-0.4 seconds typically)
- **Web UI startup**: Set timeout to 30+ seconds (starts instantly)

## Architecture Overview

### Key Files and Locations
- **Main entry points**:
  - `scribe_tools/app.py` - Unified launcher (tries GUI, falls back to web)
  - `scribe_tools/scribe_optimize.py` - Core CLI tool
  - `scribe_tools/gui.py` - Tkinter desktop GUI  
  - `scribe_tools/web_ui.py` - Flask web interface

- **Configuration**: 
  - `requirements.txt` - Python dependencies
  - `scripts/run_web_test.sh` - Test mode web launcher (zsh script, may need bash adaptation)
  - `scripts/run_web_prod.sh` - Production mode web launcher

- **Testing**:
  - `tests/generate_sample_pdf.py` - Creates test PDF with text and vector graphics
  - No automated test suite configured (manual validation only)

### Dependencies
Required Python packages (automatically installed via requirements.txt):
- pymupdf>=1.23.8 (PDF processing)
- pillow>=10.0.0 (image processing) 
- reportlab>=4.0.4 (PDF generation)
- flask>=3.0.0 (web interface)
- ebooklib>=0.18 (EPUB support)
- lxml>=4.9.0 (XML processing)

Optional system dependency:
- ghostscript (vector-preserving grayscale conversion)

### Processing Modes
1. **Vector mode** (when Ghostscript available): Preserves text and graphics as vectors while converting to grayscale
2. **Raster mode** (fallback): High-quality rasterization at specified DPI (default 300)

## Common Tasks Reference

### Repository Root Structure
```
.
├── README.md
├── requirements.txt  
├── scribe_tools/         # Main Python package
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point
│   ├── app.py           # Unified launcher
│   ├── gui.py           # Tkinter GUI
│   ├── scribe_optimize.py # Core optimization logic
│   ├── web_ui.py        # Flask web interface
│   ├── paywall.py       # Stripe integration
│   ├── scribe_epub.py   # EPUB conversion
│   └── templates/       # Web UI templates
├── scripts/             # Helper scripts
│   ├── run_web_test.sh  # Test mode launcher
│   ├── run_web_prod.sh  # Production launcher
│   └── create_issues.sh # Issue management
└── tests/
    └── generate_sample_pdf.py
```

### CLI Help Output
```
usage: scribe_optimize.py [-h] [--out OUT] [--page-size {scribe,a5,source,custom}] 
                          [--margin-pt MARGIN_PT] [--dpi DPI] [--no-autocontrast] 
                          [--no-crop] [--force-gs] [--force-raster] input

Options:
  --out OUT                    Output PDF path
  --page-size {scribe,a5,source,custom}  Final page size (default: scribe ≈ 446x595 pt)
  --margin-pt N               Inner margin in PDF points (default: 14)
  --dpi N                     Rendering DPI for raster fallback (default: 300)
  --no-autocontrast          Disable auto-contrast in raster mode
  --no-crop                   Disable margin cropping
  --force-gs                  Force Ghostscript mode
  --force-raster              Force raster mode (bypass Ghostscript)
```

### Environment Variables
- `PAYWALL_TEST_MODE=1` - Enable test mode (bypass Stripe paywall)
- `SCRIBE_UI_FORCE_WEB=1` - Force web UI instead of trying Tkinter first
- `STRIPE_SECRET_KEY` - Stripe secret key (production mode)
- `STRIPE_PRICE_ID` - Stripe price ID (production mode)  
- `BASE_URL` - Base URL for webhooks (production mode)

## Known Limitations and Workarounds

- **Tkinter not available**: Common on headless Linux. Tool automatically falls back to web UI.
- **Zsh scripts**: The shell scripts use `#!/usr/bin/env zsh` which may not be available. Run commands directly with bash if needed.
- **No automated testing**: Repository has no pytest/unittest configuration. Use manual validation scenarios above.
- **No linting tools**: No flake8, black, or mypy configured. Follow existing code style when making changes.

## Development Notes

- **No build step required**: Pure Python application, runs directly from source
- **Virtual environment required**: Always use `.venv/bin/python` for consistency
- **File cleanup**: Generated PDFs are ignored by .gitignore (*.pdf pattern)
- **Web UI state**: Paywall integration exists but test mode bypasses it completely
- **Threading**: GUI uses background threads for PDF processing to avoid UI blocking