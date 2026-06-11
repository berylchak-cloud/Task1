#!/usr/bin/env python3
"""
Hospital Bill Parser — Desktop App
Double-click to run. No command line needed.
"""

import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

# ── make sure the parser module is importable from the same folder ──
sys.path.insert(0, str(Path(__file__).parent))
from parser import extract_line_items, categorize, write_excel, CATEGORIES


# ────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hospital Bill Parser")
        self.resizable(False, False)
        self.configure(bg="#F0F4FA")
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = 520, 420
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        DARK  = "#1F3864"
        MID   = "#2F5496"
        LIGHT = "#F0F4FA"
        RED   = "#CC0000"

        # ── header ──
        hdr = tk.Frame(self, bg=DARK, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🏥  Hospital Bill Parser",
                 font=("Helvetica", 17, "bold"),
                 bg=DARK, fg="white").pack()
        tk.Label(hdr, text="Converts PDF hospital bills to categorized Excel  •  100% Offline",
                 font=("Helvetica", 9), bg=DARK, fg="#A8C0E0").pack()

        body = tk.Frame(self, bg=LIGHT, padx=28, pady=20)
        body.pack(fill="both", expand=True)

        # ── PDF selector ──
        tk.Label(body, text="Step 1 — Select your hospital bill PDF",
                 font=("Helvetica", 10, "bold"), bg=LIGHT, fg=DARK).pack(anchor="w")

        row1 = tk.Frame(body, bg=LIGHT)
        row1.pack(fill="x", pady=(4, 12))
        self.pdf_var = tk.StringVar(value="No file selected")
        tk.Label(row1, textvariable=self.pdf_var, bg="white", fg="#444",
                 relief="solid", bd=1, anchor="w", padx=6,
                 font=("Helvetica", 9), width=42).pack(side="left", fill="x", expand=True)
        tk.Button(row1, text="Browse…", command=self._browse_pdf,
                  bg=MID, fg="white", font=("Helvetica", 9, "bold"),
                  relief="flat", padx=10, cursor="hand2").pack(side="left", padx=(6,0))

        # ── Output selector ──
        tk.Label(body, text="Step 2 — Choose where to save the Excel file",
                 font=("Helvetica", 10, "bold"), bg=LIGHT, fg=DARK).pack(anchor="w")

        row2 = tk.Frame(body, bg=LIGHT)
        row2.pack(fill="x", pady=(4, 16))
        self.out_var = tk.StringVar(value="Same folder as PDF (default)")
        tk.Label(row2, textvariable=self.out_var, bg="white", fg="#444",
                 relief="solid", bd=1, anchor="w", padx=6,
                 font=("Helvetica", 9), width=42).pack(side="left", fill="x", expand=True)
        tk.Button(row2, text="Browse…", command=self._browse_out,
                  bg=MID, fg="white", font=("Helvetica", 9, "bold"),
                  relief="flat", padx=10, cursor="hand2").pack(side="left", padx=(6,0))

        # ── Run button ──
        tk.Button(body, text="▶  Convert to Excel",
                  command=self._run,
                  bg=DARK, fg="white",
                  font=("Helvetica", 12, "bold"),
                  relief="flat", pady=10, cursor="hand2",
                  activebackground="#2a4a80", activeforeground="white"
                  ).pack(fill="x", pady=(0, 12))

        # ── Progress bar ──
        self.progress = ttk.Progressbar(body, mode="indeterminate", length=460)
        self.progress.pack(fill="x", pady=(0, 8))

        # ── Log box ──
        tk.Label(body, text="Log", font=("Helvetica", 9, "bold"),
                 bg=LIGHT, fg="#555").pack(anchor="w")
        log_frame = tk.Frame(body, bg=LIGHT)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=7, font=("Courier", 9),
                           bg="#1a1a2e", fg="#b0d4ff", relief="flat",
                           state="disabled", wrap="word")
        sb = tk.Scrollbar(log_frame, command=self.log.yview)
        self.log.config(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._pdf_path  = None
        self._out_path  = None

    # ── helpers ──────────────────────────────────────────────────────

    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Select hospital bill PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if path:
            self._pdf_path = Path(path)
            self.pdf_var.set(str(self._pdf_path))
            # auto-set output to same folder
            if self._out_path is None:
                self.out_var.set("Same folder as PDF (default)")

    def _browse_out(self):
        if self._pdf_path:
            init = str(self._pdf_path.with_suffix(".xlsx"))
        else:
            init = "hospital_bill.xlsx"
        path = filedialog.asksaveasfilename(
            title="Save Excel as…",
            defaultextension=".xlsx",
            initialfile=init,
            filetypes=[("Excel files", "*.xlsx")])
        if path:
            self._out_path = Path(path)
            self.out_var.set(str(self._out_path))

    def _log(self, msg, color=None):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _run(self):
        if not self._pdf_path or not self._pdf_path.exists():
            messagebox.showerror("No file", "Please select a PDF file first.")
            return
        out = self._out_path or self._pdf_path.with_suffix(".xlsx")
        self.progress.start(12)
        self._log(f"Reading: {self._pdf_path.name} …")
        threading.Thread(target=self._process, args=(self._pdf_path, out), daemon=True).start()

    def _process(self, pdf_path: Path, out_path: Path):
        try:
            items = extract_line_items(pdf_path)
            if not items:
                self.after(0, lambda: self._done(False,
                    "No line items found.\nThe PDF may be a scanned image — "
                    "install Tesseract OCR and try again."))
                return

            for item in items:
                if "category" not in item:
                    item["category"] = categorize(item["description"])

            from collections import Counter
            counts = Counter(item["category"] for item in items)
            summary = "\n".join(f"  {cat}: {n}" for cat, n in counts.items())
            self._log(f"Extracted {len(items)} line items:\n{summary}")

            write_excel(items, out_path)
            self.after(0, lambda: self._done(True, str(out_path)))

        except Exception as e:
            self.after(0, lambda: self._done(False, str(e)))

    def _done(self, success: bool, msg: str):
        self.progress.stop()
        if success:
            self._log(f"✓ Saved: {msg}")
            if messagebox.askyesno("Done!",
                    f"Excel file saved!\n\n{msg}\n\nOpen it now?"):
                import os, subprocess
                if sys.platform == "win32":
                    os.startfile(msg)
                elif sys.platform == "darwin":
                    subprocess.call(["open", msg])
                else:
                    subprocess.call(["xdg-open", msg])
        else:
            self._log(f"✗ Error: {msg}")
            messagebox.showerror("Error", msg)


if __name__ == "__main__":
    app = App()
    app.mainloop()
