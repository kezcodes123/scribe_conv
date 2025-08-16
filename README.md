# Kindle Scribe PDF Optimizer

Make existing PDFs easier to read on Kindle Scribe without changing any words or illustrations. The tool:

- Converts pages to grayscale (preserving vector text/graphics when Ghostscript is available)
- Boosts readability for monochrome displays
- Auto-crops excess white margins
- Fits content onto Kindle Scribe–friendly pages (default) or A5, with gentle margins

It does not rewrite or reflow text, nor remove or alter illustrations—only formatting, page size, and grayscale conversion suitable for Scribe’s black-and-white screen.

## Features
- Vector-preserving grayscale via Ghostscript when available.
- Fallback to high-quality raster pipeline (PyMuPDF + Pillow) if Ghostscript is not installed.
- Auto margin crop per page with a safe inner margin.
- Page size presets: `scribe` (default), `a5`, or `source`.

## Usage

1) Place your input PDF anywhere on disk. 

2) GUI (auto-detects best option):

```bash
python -m scribe_tools.app
```

3) CLI (replace /path/to/input.pdf accordingly):

```bash
python -m scribe_tools.scribe_optimize /path/to/input.pdf
```

This will produce `/path/to/input_scribe.pdf` by default.

### Options
- `--out OUTFILE` – specify output path
- `--page-size {scribe,a5,source}` – choose final page size; `scribe` ≈ 446x595 pt, `a5` = 420x595 pt, `source` keeps original size
- `--margin-pt N` – inner margin in PDF points (1pt = 1/72 inch), default 14
- `--dpi N` – rendering DPI for raster fallback, default 300
- `--no-autocontrast` – disable gentle auto-contrast in raster fallback

## Install

The project uses Python with a few packages. Install them in your environment:

```bash
pip install -r requirements.txt
```

Optional but recommended: install Ghostscript on macOS for vector-preserving grayscale:

```bash
brew install ghostscript
```

## Test with a sample PDF
Generate a small sample PDF and optimize it:

```bash
python tests/generate_sample_pdf.py
python -m scribe_tools.scribe_optimize tests/sample.pdf --out tests/sample_scribe.pdf
```

## Notes
- If Ghostscript is present, grayscale conversion preserves vector text and drawings.
- Margin cropping is detected via a low-res render, but cropping is applied non-destructively when preserving vectors.
- If Ghostscript is missing, the fallback raster pipeline creates grayscale page images sized for Scribe.
- On some macOS Python builds, Tkinter isn’t available by default. The unified launcher automatically falls back to a local web UI on http://127.0.0.1:5000.
