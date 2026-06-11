#!/usr/bin/env python3
"""
hospital_bill_parser/parser.py

Reads a hospital bill PDF, extracts line items, categorizes them,
and exports to a formatted Excel file. Runs fully offline.

Usage:
    python parser.py <bill.pdf> [--out output.xlsx]
"""

import re
import sys
import argparse
from pathlib import Path

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Category definitions — keywords mapped to category name
# ---------------------------------------------------------------------------
CATEGORIES = {
    "Room & Board": [
        "room", "board", "accommodation", "ward", "bed", "admission",
        "inpatient", "overnight", "daily charge", "hospital stay", "nursing",
    ],
    "Operating Room": [
        "operating room", "or fee", "theatre", "theater", "operation room",
        "surgical suite", "recovery room", "post-op", "pre-op",
    ],
    "Surgeon's Fee": [
        "surgeon", "surgical fee", "surgeon fee", "operative fee",
        "surgery fee", "surgical charge",
    ],
    "Anaesthetist's Fee": [
        "anaesth", "anesthes", "anesthetist", "anaesthetist",
        "anaesthesia", "anesthesia", "sedation",
    ],
    "Professional Fee": [
        "professional fee", "doctor fee", "physician fee", "consultant fee",
        "specialist fee", "attending fee", "medical fee", "dr.", "dr ",
        "consultation", "visit charge", "ward round",
    ],
    "Not Covered by Insurance": [
        "not covered", "non-covered", "exclusion", "cosmetic",
        "elective", "experimental", "investigational", "personal",
        "telephone", "tv", "television", "wifi", "internet",
        "newspaper", "guest meal", "comfort", "amenity",
    ],
    "Miscellaneous": [],  # catch-all — assigned last
}

CATEGORY_COLORS = {
    "Room & Board":              "D6E4F0",
    "Operating Room":            "FCE4D6",
    "Surgeon's Fee":             "E2EFDA",
    "Anaesthetist's Fee":        "FFF2CC",
    "Professional Fee":          "EAD1DC",
    "Not Covered by Insurance":  "F4CCCC",
    "Miscellaneous":             "EFEFEF",
}


def categorize(description: str) -> str:
    text = description.lower()
    for category, keywords in CATEGORIES.items():
        if category == "Miscellaneous":
            continue
        if any(kw in text for kw in keywords):
            return category
    return "Miscellaneous"


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------
MONEY_RE = re.compile(r"[\d,]+\.?\d*")


def looks_like_amount(token: str) -> bool:
    return bool(re.fullmatch(r"[\d,]+\.?\d*", token.replace(",", "")))


def extract_text_from_scanned(pdf_path: Path) -> str:
    """Use OCR (tesseract) to extract text from a scanned/image-based PDF. Fully offline."""
    print("  Scanned PDF detected — running OCR (this may take a moment)...")
    pages = convert_from_path(pdf_path, dpi=300)
    all_text = []
    for i, page_img in enumerate(pages, 1):
        print(f"  OCR page {i}/{len(pages)}...")
        text = pytesseract.image_to_string(page_img, lang="eng")
        all_text.append(text)
    return "\n".join(all_text)


def is_text_based(pdf_path: Path) -> bool:
    """Returns True if the PDF contains selectable text (not a pure scan)."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                return True
    return False


def parse_lines(text: str) -> list[dict]:
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 4:
            continue
        tokens = line.split()
        if len(tokens) < 2:
            continue
        amount = ""
        desc_tokens = []
        for tok in reversed(tokens):
            clean = tok.replace(",", "").replace(".", "")
            if not amount and clean.isdigit() and len(clean) >= 2:
                amount = tok
            else:
                desc_tokens.insert(0, tok)
        description = " ".join(desc_tokens).strip()
        if description and len(description) > 3:
            items.append({"description": description, "amount": amount, "raw": line})
    return items


def extract_line_items(pdf_path: Path) -> list[dict]:
    """
    Extract rows from PDF. Auto-detects text-based vs scanned and uses OCR if needed.
    Returns list of {"description": str, "amount": str, "raw": str}.
    """
    items = []

    if is_text_based(pdf_path):
        # Text-based PDF: use pdfplumber tables + text
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            cells = [c.strip() if c else "" for c in row]
                            non_empty = [c for c in cells if c]
                            if len(non_empty) < 2:
                                continue
                            desc_parts = []
                            amount = ""
                            for cell in reversed(cells):
                                if not amount and looks_like_amount(cell.replace(",", "").replace(".", "")):
                                    amount = cell
                                else:
                                    if cell:
                                        desc_parts.insert(0, cell)
                            description = " ".join(desc_parts).strip()
                            if description and len(description) > 2:
                                items.append({"description": description, "amount": amount, "raw": " | ".join(non_empty)})
                else:
                    text = page.extract_text() or ""
                    items.extend(parse_lines(text))
    else:
        # Scanned PDF: OCR with tesseract (offline)
        text = extract_text_from_scanned(pdf_path)
        items.extend(parse_lines(text))

    return items


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

def make_border():
    thin = Side(style="thin")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def write_excel(items: list[dict], out_path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hospital Bill"

    # Group items by category
    grouped: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for item in items:
        grouped[item["category"]].append(item)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="2F5496")
    cat_font = Font(bold=True)
    total_font = Font(bold=True, italic=True)
    border = make_border()
    center = Alignment(horizontal="center", vertical="center")

    # Title row
    ws.merge_cells("A1:D1")
    title_cell = ws["A1"]
    title_cell.value = "Hospital Bill — Categorized Summary"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="1F3864")
    title_cell.alignment = center
    ws.row_dimensions[1].height = 28

    # Column headers
    headers = ["Category", "Description", "Amount", "Note"]
    ws.append(headers)
    for col, _ in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center
    ws.row_dimensions[2].height = 18

    current_row = 3
    grand_total = 0.0

    for category, cat_items in grouped.items():
        if not cat_items:
            continue

        color = CATEGORY_COLORS.get(category, "FFFFFF")
        cat_fill = PatternFill("solid", fgColor=color)

        # Category header row
        ws.merge_cells(f"A{current_row}:D{current_row}")
        cat_cell = ws.cell(row=current_row, column=1)
        cat_cell.value = f"  {category}"
        cat_cell.font = Font(bold=True, size=11)
        cat_cell.fill = PatternFill("solid", fgColor=color)
        cat_cell.border = border
        ws.row_dimensions[current_row].height = 16
        current_row += 1

        cat_total = 0.0
        for item in cat_items:
            ws.cell(row=current_row, column=1).value = category
            ws.cell(row=current_row, column=2).value = item["description"]
            ws.cell(row=current_row, column=3).value = item["amount"]
            ws.cell(row=current_row, column=4).value = item.get("note", "")

            # Parse amount for totaling
            try:
                cat_total += float(item["amount"].replace(",", ""))
            except (ValueError, AttributeError):
                pass

            for col in range(1, 5):
                cell = ws.cell(row=current_row, column=col)
                cell.fill = cat_fill
                cell.border = border
                cell.alignment = Alignment(vertical="center")
            current_row += 1

        # Category subtotal
        ws.cell(row=current_row, column=2).value = f"Subtotal — {category}"
        ws.cell(row=current_row, column=3).value = f"{cat_total:,.2f}" if cat_total else ""
        for col in range(1, 5):
            cell = ws.cell(row=current_row, column=col)
            cell.font = total_font
            cell.fill = PatternFill("solid", fgColor=color)
            cell.border = border
        current_row += 1
        grand_total += cat_total

        # Spacer
        current_row += 1

    # Grand total
    ws.cell(row=current_row, column=2).value = "GRAND TOTAL"
    ws.cell(row=current_row, column=3).value = f"{grand_total:,.2f}" if grand_total else ""
    for col in range(1, 5):
        cell = ws.cell(row=current_row, column=col)
        cell.font = Font(bold=True, size=12, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3864")
        cell.border = border

    # Column widths
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 48
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 22

    wb.save(out_path)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Convert a hospital bill PDF to categorized Excel.")
    parser.add_argument("pdf", help="Path to the hospital bill PDF")
    parser.add_argument("--out", help="Output Excel file (default: same name as PDF)", default=None)
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.is_file():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    out_path = Path(args.out) if args.out else pdf_path.with_suffix(".xlsx")

    print(f"Reading: {pdf_path}")
    items = extract_line_items(pdf_path)

    if not items:
        print("No line items found. The PDF may be scanned (image-based). Try OCR first.")
        sys.exit(1)

    # Categorize
    for item in items:
        item["category"] = categorize(item["description"])

    # Summary
    from collections import Counter
    counts = Counter(item["category"] for item in items)
    print(f"\nExtracted {len(items)} line item(s):")
    for cat, count in counts.items():
        print(f"  {cat}: {count}")

    write_excel(items, out_path)


if __name__ == "__main__":
    main()
