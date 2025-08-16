#!/usr/bin/env python3
"""
Simple GUI for Kindle Scribe PDF Optimizer (Tkinter)

Run with:
    python -m scribe_tools.gui
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .scribe_optimize import optimize_pdf, has_ghostscript


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Kindle Scribe PDF Optimizer")
        self.minsize(560, 360)

        self.in_path = tk.StringVar()
        self.out_path = tk.StringVar()
        self.page_size = tk.StringVar(value="scribe")
        self.margin_pt = tk.IntVar(value=14)
        self.dpi = tk.IntVar(value=300)
        self.autocontrast = tk.BooleanVar(value=True)
        self.crop = tk.BooleanVar(value=True)

        self._build_ui()
        self._update_ghostscript_status()

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}

        # Input
        fr_in = ttk.LabelFrame(self, text="Input PDF")
        fr_in.pack(fill=tk.X, **pad)
        ttk.Entry(fr_in, textvariable=self.in_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 6), pady=10)
        ttk.Button(fr_in, text="Browse…", command=self.browse_in).pack(side=tk.LEFT, padx=(0, 10), pady=10)

        # Output
        fr_out = ttk.LabelFrame(self, text="Output PDF (optional)")
        fr_out.pack(fill=tk.X, **pad)
        ttk.Entry(fr_out, textvariable=self.out_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 6), pady=10)
        ttk.Button(fr_out, text="Choose…", command=self.browse_out).pack(side=tk.LEFT, padx=(0, 10), pady=10)

        # Options
        fr_opts = ttk.LabelFrame(self, text="Options")
        fr_opts.pack(fill=tk.BOTH, expand=True, **pad)

        # Page size radios
        radios = ttk.Frame(fr_opts)
        radios.pack(fill=tk.X, padx=10, pady=(10, 6))
        ttk.Label(radios, text="Page size:").pack(side=tk.LEFT)
        for label, val in [("Scribe", "scribe"), ("A5", "a5"), ("Source", "source")]:
            ttk.Radiobutton(radios, text=label, value=val, variable=self.page_size).pack(side=tk.LEFT, padx=8)

        # Crop and contrast
        toggles = ttk.Frame(fr_opts)
        toggles.pack(fill=tk.X, padx=10, pady=6)
        ttk.Checkbutton(toggles, text="Crop margins", variable=self.crop).pack(side=tk.LEFT)
        ttk.Checkbutton(toggles, text="Auto-contrast", variable=self.autocontrast).pack(side=tk.LEFT, padx=16)

        # Margin and DPI
        grid = ttk.Frame(fr_opts)
        grid.pack(fill=tk.X, padx=10, pady=(6, 10))
        ttk.Label(grid, text="Margin (pt):").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(grid, from_=0, to=72, increment=1, textvariable=self.margin_pt, width=6).grid(row=0, column=1, sticky=tk.W, padx=(6, 20))
        ttk.Label(grid, text="DPI (fallback):").grid(row=0, column=2, sticky=tk.W)
        ttk.Spinbox(grid, from_=72, to=600, increment=12, textvariable=self.dpi, width=6).grid(row=0, column=3, sticky=tk.W, padx=(6, 20))

        # Ghostscript status
        self.gs_label = ttk.Label(fr_opts, text="")
        self.gs_label.pack(anchor=tk.W, padx=10, pady=(0, 6))

        # Run button + status
        fr_run = ttk.Frame(self)
        fr_run.pack(fill=tk.X, **pad)
        self.run_btn = ttk.Button(fr_run, text="Optimize", command=self.on_run)
        self.run_btn.pack(side=tk.RIGHT)
        self.status = ttk.Label(fr_run, text="")
        self.status.pack(side=tk.LEFT)

    def _update_ghostscript_status(self) -> None:
        if has_ghostscript():
            self.gs_label.configure(text="Ghostscript detected (vector-preserving grayscale enabled)")
        else:
            self.gs_label.configure(text="Ghostscript not found (using raster fallback)")

    def browse_in(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose input PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self.in_path.set(path)

    def browse_out(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save output PDF as…",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.out_path.set(path)

    def on_run(self) -> None:
        in_pdf = self.in_path.get().strip()
        out_pdf = self.out_path.get().strip()

        if not in_pdf:
            messagebox.showerror("Missing input", "Please choose an input PDF.")
            return
        if not os.path.exists(in_pdf):
            messagebox.showerror("Not found", f"Input not found:\n{in_pdf}")
            return
        if not out_pdf:
            base, _ = os.path.splitext(in_pdf)
            suffix = {
                "scribe": "_scribe.pdf",
                "a5": "_a5.pdf",
                "source": "_source.pdf" if self.crop.get() else "_source-nocrop.pdf",
            }[self.page_size.get()]
            out_pdf = base + suffix
            self.out_path.set(out_pdf)

        self._set_busy(True)
        self.status.configure(text="Running…")

        def worker():
            try:
                optimize_pdf(
                    in_pdf,
                    out_pdf,
                    page_size=self.page_size.get(),
                    margin_pt=int(self.margin_pt.get()),
                    dpi=int(self.dpi.get()),
                    autocontrast=bool(self.autocontrast.get()),
                    crop=bool(self.crop.get()),
                )
                self.after(0, lambda: self._on_done(out_pdf))
            except Exception as e:
                self.after(0, lambda: self._on_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, out_pdf: str) -> None:
        self._set_busy(False)
        self.status.configure(text="Done")
        messagebox.showinfo("Completed", f"Wrote\n{out_pdf}")

    def _on_error(self, e: Exception) -> None:
        self._set_busy(False)
        self.status.configure(text="Error")
        messagebox.showerror("Error", f"Optimization failed:\n{e}")

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.run_btn.configure(state=state)


def main() -> None:
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        # Re-raise to allow unified launcher to fall back to web UI
        raise


if __name__ == "__main__":
    main()
