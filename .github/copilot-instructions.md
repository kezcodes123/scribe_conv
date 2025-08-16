# Kindle Scribe PDF Optimizer

Kindle Scribe PDF Optimizer is a Python application that optimizes PDFs for reading on Kindle Scribe devices. The tool converts PDFs to grayscale, crops margins, and resizes pages while preserving text quality and vector graphics when possible.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Bootstrap and Setup
- Install Python dependencies: `python3 -m pip install -r requirements.txt`
  - Takes <5 seconds. Dependencies: PyMuPDF, Pillow, ReportLab, Flask, EbookLib, lxml
  - NEVER CANCEL: Set timeout to 60+ seconds for first-time installs on slow networks
- Verify installation: `python3 -c "import scribe_tools; print('Installation successful')"`

### Running the Application
- **CLI optimization**: `python3 -m scribe_tools.scribe_optimize input.pdf --out output.pdf`
  - Processing time: 0.3-2 seconds for typical PDFs, up to 30 seconds for large files
  - NEVER CANCEL: Set timeout to 120+ seconds for CLI operations
- **GUI application**: `python3 -m scribe_tools.gui` 
  - Requires Tkinter (fails gracefully in headless environments)
- **Web UI (unified launcher)**: `python3 -m scribe_tools.app`
  - Auto-detects GUI availability, falls back to web UI on http://127.0.0.1:[random-port]
  - NEVER CANCEL: Set timeout to 30+ seconds for web UI startup
- **Web UI test mode**: `PAYWALL_TEST_MODE=1 SCRIBE_UI_FORCE_WEB=1 python3 -m scribe_tools.app`
  - Bypasses paywall for testing, forces web interface

### Testing and Validation
- **Generate test PDF**: `python3 tests/generate_sample_pdf.py`
  - Creates `tests/sample.pdf` in <1 second
- **Test optimization**: `python3 -m scribe_tools.scribe_optimize tests/sample.pdf --out tests/sample_scribe.pdf`
  - Verifies core functionality, completes in <1 second
- **CRITICAL VALIDATION SCENARIO**: After making changes, ALWAYS run this complete test:
  ```bash
  python3 tests/generate_sample_pdf.py
  python3 -m scribe_tools.scribe_optimize tests/sample.pdf --out tests/sample_scribe.pdf
  ls -la tests/sample_scribe.pdf  # Verify output file exists and has reasonable size
  ```

## Application Architecture

### Core Modules
- **scribe_tools/scribe_optimize.py** - Main CLI and optimization engine
- **scribe_tools/app.py** - Unified launcher (GUI fallback to web)
- **scribe_tools/gui.py** - Tkinter desktop interface
- **scribe_tools/web_ui.py** - Flask web interface with paywall
- **scribe_tools/scribe_epub.py** - EPUB conversion functionality
- **scribe_tools/paywall.py** - Stripe payment integration

### Project Structure
```
scribe_tools/
├── __init__.py
├── __main__.py         # Entry point for -m scribe_tools
├── app.py             # Unified launcher
├── gui.py             # Tkinter GUI
├── web_ui.py          # Flask web app
├── scribe_optimize.py # Core optimization engine
├── scribe_epub.py     # EPUB functionality  
├── paywall.py         # Payment system
└── templates/         # HTML templates
    ├── index.html
    └── pricing.html
scripts/
├── run_web_test.sh    # Start web UI in test mode
├── run_web_prod.sh    # Start web UI in production
└── create_issues.sh   # GitHub issue management
tests/
└── generate_sample_pdf.py  # Test PDF generator
```

### Key CLI Options (scribe_optimize.py)
- `--page-size {scribe,a5,source,custom}` - Output page size (default: scribe ≈ 446x595 pt)
- `--margin-pt N` - Inner margin in points (default: 14)
- `--dpi N` - Rendering DPI for raster fallback (default: 300)
- `--no-autocontrast` - Disable contrast enhancement
- `--no-crop` - Disable margin cropping
- `--force-raster` - Force raster pipeline (bypass Ghostscript)
- `--gs-quality {screen,ebook,printer,prepress,default}` - Ghostscript quality setting

## Development Workflow

### Making Changes
1. **ALWAYS validate setup first**: Run the critical validation scenario above
2. **Test functionality**: Ensure PDF optimization produces valid output files
3. **Check web UI**: Start web UI and verify it loads without errors
4. **Manual validation**: Test specific features you've modified

### Common Tasks

#### Testing Different PDF Processing Options
```bash
# Test different page sizes
python3 -m scribe_tools.scribe_optimize tests/sample.pdf --page-size a5 --out tests/sample_a5.pdf
python3 -m scribe_tools.scribe_optimize tests/sample.pdf --page-size source --out tests/sample_source.pdf

# Test with no cropping
python3 -m scribe_tools.scribe_optimize tests/sample.pdf --no-crop --out tests/sample_nocrop.pdf

# Test raster fallback
python3 -m scribe_tools.scribe_optimize tests/sample.pdf --force-raster --out tests/sample_raster.pdf
```

#### Web UI Development
```bash
# Start in test mode (no paywall)
PAYWALL_TEST_MODE=1 SCRIBE_UI_FORCE_WEB=1 python3 -m scribe_tools.app

# The web UI will be available at http://127.0.0.1:[port]
# Test file upload and PDF processing through the web interface
```

### Environment Variables
- `PAYWALL_TEST_MODE=1` - Bypasses Stripe paywall for testing
- `SCRIBE_UI_FORCE_WEB=1` - Forces web UI instead of trying GUI first
- `STRIPE_SECRET_KEY` - Stripe secret key for production paywall
- `STRIPE_PRICE_ID` - Stripe price ID for subscriptions
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret for payment processing

## Technical Details

### Dependencies and Optional Components
- **Ghostscript**: Optional system dependency for vector-preserving grayscale conversion
  - When missing: Falls back to high-quality raster pipeline (PyMuPDF + Pillow)
  - Install on macOS: `brew install ghostscript`
  - Install on Ubuntu: `apt-get install ghostscript`
- **Tkinter**: Required for GUI, often missing on some Python builds
  - When missing: Unified launcher automatically falls back to web UI

### Performance Characteristics
- **Small PDFs (1-5 pages)**: 0.3-1 second processing time
- **Medium PDFs (10-50 pages)**: 1-10 seconds processing time  
- **Large PDFs (100+ pages)**: 10-60 seconds processing time
- **NEVER CANCEL**: Always allow at least 120 seconds timeout for PDF processing operations
- **Dependency installation**: <5 seconds when cached, up to 60 seconds for fresh installs

### File Handling
- Input: Any PDF file
- Output: Optimized PDF with suffix `_scribe.pdf` by default
- Temporary files: Handled automatically, cleaned up after processing
- No build artifacts or compilation required

## Validation and Testing

### Required Manual Validation Steps
After making any changes, ALWAYS perform these validation steps:

1. **Basic functionality test**:
   ```bash
   python3 tests/generate_sample_pdf.py
   python3 -m scribe_tools.scribe_optimize tests/sample.pdf --out tests/validation.pdf
   # Verify tests/validation.pdf exists and is larger than original (~177KB vs ~2.6KB)
   ls -la tests/validation.pdf
   ```

2. **Web UI test**:
   ```bash
   # Start web UI (will auto-assign port)
   PAYWALL_TEST_MODE=1 SCRIBE_UI_FORCE_WEB=1 python3 -m scribe_tools.app &
   # Verify it starts without errors and serves on localhost
   # Look for "Running on http://127.0.0.1:[port]" in output
   # Stop with Ctrl+C
   ```

3. **Module import test**:
   ```bash
   python3 -c "from scribe_tools import scribe_optimize, web_ui, scribe_epub; print('Core modules import successfully')"
   # Note: GUI module will fail in headless environments due to missing tkinter
   ```

4. **Complete end-to-end web UI validation** (when possible):
   - Start web UI in test mode
   - Navigate to the displayed URL
   - Upload a test PDF file using the file picker
   - Click "Optimize" button 
   - Verify optimized PDF downloads automatically
   - Check that processing completes in <5 seconds for small files

### File Size Validation
- Original sample PDF: ~2.6KB (generated test file)
- Optimized sample PDF: Should be significantly larger (~177KB) due to rasterization process
- Web UI should start and bind to a port (check output for "Running on http://127.0.0.1:[port]")
- Processing time: <1 second for sample PDF, up to 5 seconds for typical documents

### Error Conditions to Test
- **Invalid PDF**: Test with non-PDF file - should fail gracefully with clear error
- **Missing input**: Test with non-existent file - should exit with error code 1
- **Web UI without test mode**: Should redirect to pricing page when paywall active

## Common Patterns and Troubleshooting

### If PDF optimization fails:
1. Check input file exists and is valid PDF
2. Try with `--force-raster` flag to bypass Ghostscript issues
3. Check available disk space for temporary files
4. Verify all dependencies are installed correctly

### If web UI won't start:
1. Check if port is already in use
2. Verify Flask and dependencies are installed
3. Check environment variables are set correctly for test mode

### If GUI fails:
1. Expected behavior in headless environments - should fall back to web UI
2. In desktop environments, verify Tkinter is available

**Remember**: This is a PDF processing tool, not a build system. No compilation, no complex build steps, no test runners - just Python modules that process PDFs efficiently.

## Performance Tips for Agents

### Efficient Development Workflow
- **Always test with the sample PDF first** - it processes in <1 second and validates core functionality
- **Use `--force-raster` for consistent behavior** - bypasses Ghostscript availability issues  
- **Start web UI in test mode for UI testing** - `PAYWALL_TEST_MODE=1` bypasses authentication
- **Process multiple files in sequence** - no cleanup needed between runs
- **Check file sizes to verify processing** - optimized files are typically 50-100x larger than input

### When Things Don't Work
- **PDF optimization fails**: Try `--force-raster`, verify input file is valid PDF
- **Web UI crashes**: Check environment variables, verify all dependencies installed  
- **Import errors**: Run `python3 -m pip install -r requirements.txt` again
- **GUI fails**: Expected in headless environments - unified launcher will fallback to web UI
- **Long processing times**: Normal for large PDFs - always set 120+ second timeouts

### Quick Commands Reference
```bash
# Setup (once per environment)
python3 -m pip install -r requirements.txt

# Basic validation (30 seconds)
python3 tests/generate_sample_pdf.py
python3 -m scribe_tools.scribe_optimize tests/sample.pdf --out tests/test.pdf

# Web UI testing (starts immediately)
PAYWALL_TEST_MODE=1 SCRIBE_UI_FORCE_WEB=1 python3 -m scribe_tools.app

# CLI with different options (each <1 second)
python3 -m scribe_tools.scribe_optimize input.pdf --page-size a5
python3 -m scribe_tools.scribe_optimize input.pdf --no-crop --force-raster
```