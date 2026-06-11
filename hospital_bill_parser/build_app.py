#!/usr/bin/env python3
"""
Packages the app into a standalone executable using PyInstaller.
Run once:  python build_app.py
Output:
  Windows → dist/HospitalBillParser.exe
  Mac     → dist/HospitalBillParser.app
  Linux   → dist/HospitalBillParser
"""
import subprocess, sys

subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller",
                "pdfplumber", "openpyxl", "pytesseract", "pdf2image"], check=True)

subprocess.run([
    "pyinstaller",
    "--onefile",
    "--windowed",
    "--name", "HospitalBillParser",
    "--add-data", f"parser.py{':' if sys.platform != 'win32' else ';'}.",
    "app.py"
], check=True)

print("\n✓ Done! Find your app in the  dist/  folder.")
