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
    # UB-04 revenue codes 010X — inpatient accommodation
    "Room & Board": [
        "room", "board", "accommodation", "ward", "bed", "admission",
        "inpatient", "overnight", "daily charge", "hospital stay",
        "private room", "semi-private", "isolation room", "step-down",
        "telemetry", "nursery", "newborn", "maternity",
    ],
    # UB-04 revenue codes 020X — ICU / intensive care
    "ICU / Intensive Care": [
        "icu", "intensive care", "critical care", "ccu", "coronary care",
        "nicu", "picu", "burn unit", "high dependency", "hdu",
        "cardiac intensive", "step down unit",
    ],
    # UB-04 revenue codes 036X — operating room / theatre
    "Operating Room": [
        "operating room", "operating theatre", "operating theater",
        "or fee", "theatre fee", "theater fee", "operation room",
        "surgical suite", "recovery room", "post-op", "pre-op",
        "surgical supply", "surgical supplies", "sterile", "draping",
        "cell salvage", "intra-operative", "post-operative recovery",
        "laparoscop", "endoscop",
    ],
    # Surgeon fees
    "Surgeon's Fee": [
        "surgeon", "surgical fee", "surgeon fee", "operative fee",
        "surgery fee", "surgical charge", "assistant surgeon",
        "primary surgeon", "operating surgeon",
    ],
    # UB-04 revenue codes 037X — anesthesia
    "Anaesthetist's Fee": [
        "anaesth", "anesthes", "anesthetist", "anaesthetist",
        "anaesthesia", "anesthesia", "sedation", "anaesthesia drug",
        "anesthesia agent", "general anaesthesia", "spinal block",
        "epidural", "nerve block",
    ],
    # Professional / doctor fees
    "Professional Fee": [
        "professional fee", "doctor fee", "physician fee", "consultant fee",
        "specialist fee", "attending fee", "medical fee", "dr.", "dr ",
        "consultation", "visit charge", "ward round", "referral fee",
        "cardiologist", "radiologist", "pathologist", "internist",
        "attending physician", "ward consultation",
    ],
    # UB-04 revenue codes 030X — laboratory
    "Laboratory": [
        "laboratory", "lab fee", "blood count", "cbc", "metabolic panel",
        "blood gas", "abg", "coagulation", "pt/", "aptt", "inr",
        "blood culture", "urinalysis", "urine culture", "serology",
        "histopathology", "biopsy", "pathology", "culture", "sensitivity",
        "hematology", "biochemistry", "lipid profile", "thyroid",
        "glucose", "creatinine", "troponin", "d-dimer",
    ],
    # UB-04 revenue codes 032X — radiology / imaging
    "Radiology / Imaging": [
        "radiology", "x-ray", "xray", "ct scan", "mri", "ultrasound",
        "ecg", "ekg", "electrocardiogram", "echo", "echocardiogram",
        "mammogram", "fluoroscopy", "nuclear", "pet scan", "doppler",
        "angiogram", "imaging", "radiograph", "scan",
    ],
    # UB-04 revenue codes 025X — pharmacy
    "Pharmacy / Medications": [
        "pharmacy", "medication", "medicine", "drug", "iv fluid",
        "normal saline", "lactated", "dextrose", "antibiotic",
        "cefazolin", "metronidazole", "morphine", "paracetamol",
        "ondansetron", "pantoprazole", "enoxaparin", "heparin",
        "insulin", "steroid", "analgesic", "anticoagulant",
        "prophylaxis", "intravenous", "oral medication",
    ],
    # Items not covered by standard insurance (UB-04 rev code 099X extras)
    "Not Covered by Insurance": [
        "not covered", "non-covered", "non covered", "exclusion",
        "cosmetic", "experimental", "investigational", "elective",
        "personal", "telephone", "tv ", "television", "wifi",
        "internet", "newspaper", "guest meal", "comfort kit",
        "amenity", "take-home", "retail medication", "beauty",
        "private nurse", "special nurse", "uplift", "upgrade",
    ],
    "Miscellaneous": [],  # catch-all — assigned last
}

CATEGORY_COLORS = {
    "Room & Board":              "D6E4F0",
    "ICU / Intensive Care":      "C9DAF8",
    "Operating Room":            "FCE4D6",
    "Surgeon's Fee":             "E2EFDA",
    "Anaesthetist's Fee":        "FFF2CC",
    "Professional Fee":          "EAD1DC",
    "Laboratory":                "D9EAD3",
    "Radiology / Imaging":       "FFE599",
    "Pharmacy / Medications":    "D9D2E9",
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

DATE_RE = re.compile(
    r"\b(\d{1,2}[-/]\w{2,9}[-/]\d{2,4}"   # 10-Nov-2024, 10/11/2024
    r"|\d{1,2}\s+\w+\s+\d{4}"              # 10 November 2024
    r"|\w{3,9}\s+\d{1,2},?\s+\d{4}"        # November 10, 2024
    r"|\d{4}[-/]\d{2}[-/]\d{2})\b"         # 2024-11-10
)


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


# Maps section header keywords found IN the bill to our standard category names
SECTION_HEADER_MAP = {
    "room":              "Room & Board",
    "bed":               "Room & Board",
    "accommodation":     "Room & Board",
    "ward charge":       "Room & Board",
    "nursing charge":    "Room & Board",
    "icu":               "ICU / Intensive Care",
    "intensive care":    "ICU / Intensive Care",
    "critical care":     "ICU / Intensive Care",
    "theatre":           "Operating Room",
    "theater":           "Operating Room",
    "operating room":    "Operating Room",
    "operating theatre": "Operating Room",
    "surgeon":           "Surgeon's Fee",
    "surgical fee":      "Surgeon's Fee",
    "anaesth":           "Anaesthetist's Fee",
    "anesthes":          "Anaesthetist's Fee",
    "professional fee":  "Professional Fee",
    "physician fee":     "Professional Fee",
    "doctor fee":        "Professional Fee",
    "diagnostic":        "Laboratory",
    "laboratory":        "Laboratory",
    "lab ":              "Laboratory",
    "radiology":         "Radiology / Imaging",
    "imaging":           "Radiology / Imaging",
    "pharmacy":          "Pharmacy / Medications",
    "medication":        "Pharmacy / Medications",
    "drug":              "Pharmacy / Medications",
    "miscellaneous":     "Not Covered by Insurance",
    "non-covered":       "Not Covered by Insurance",
    "not covered":       "Not Covered by Insurance",
}

def section_header_to_category(header: str) -> str:
    h = header.lower()
    for kw, cat in SECTION_HEADER_MAP.items():
        if kw in h:
            return cat
    return None


# ---------------------------------------------------------------------------
# Patient / claim detection — splits a batch PDF into separate claims
# ---------------------------------------------------------------------------

# Keywords that signal the START of a new hospital claim (bill header)
CLAIM_START_SIGNALS = [
    "patient name", "patient no", "patient id", "admission date",
    "date admitted", "date of admission", "bill no", "bill number",
    "invoice no", "invoice number", "account no", "claim no",
    "hospital bill", "statement of account", "itemized bill",
]

# Keywords that mark a page as a REPORT (not a bill)
REPORT_SIGNALS = [
    "discharge summary", "clinical notes", "medical report",
    "doctor's report", "physician report", "operative notes",
    "pathology report", "radiology report", "laboratory report",
    "nursing notes", "progress notes", "history and physical",
    "consultation report",
]


def _page_text(page) -> str:
    """Extract plain text from a pdfplumber page."""
    return (page.extract_text() or "").lower()


def _is_claim_start(text: str) -> bool:
    return sum(1 for kw in CLAIM_START_SIGNALS if kw in text) >= 2


def _is_report_page(text: str) -> bool:
    return any(kw in text for kw in REPORT_SIGNALS)


def _extract_patient_info(page) -> dict:
    """Pull patient name, bill no, admission date from a header page."""
    info = {"patient": "", "bill_no": "", "admitted": "", "discharged": ""}
    text = page.extract_text() or ""
    for line in text.splitlines():
        ll = line.lower()
        if any(k in ll for k in ("patient name", "patient:")):
            val = re.split(r"[:：]", line, maxsplit=1)
            if len(val) > 1:
                info["patient"] = val[1].strip()[:40]
        if any(k in ll for k in ("bill no", "invoice no", "account no", "claim no")):
            val = re.split(r"[:：]", line, maxsplit=1)
            if len(val) > 1:
                info["bill_no"] = val[1].strip()[:20]
        if any(k in ll for k in ("date admitted", "admission date", "admitted")):
            val = re.split(r"[:：]", line, maxsplit=1)
            if len(val) > 1:
                info["admitted"] = val[1].strip()[:20]
        if any(k in ll for k in ("date discharged", "discharge date", "discharged")):
            val = re.split(r"[:：]", line, maxsplit=1)
            if len(val) > 1:
                info["discharged"] = val[1].strip()[:20]
    return info


def split_into_claims(pdf_path: Path) -> list[dict]:
    """
    Scans a batch PDF and splits it into separate claims + report pages.

    Returns a list of claim dicts:
      {
        "label":      "Claim 1 — DELA CRUZ, JUAN (Bill: MGH-001)",
        "page_start": 1,
        "page_end":   20,
        "type":       "claim" | "report" | "unknown",
        "info":       { patient, bill_no, admitted, discharged }
      }
    """
    claims = []
    current = None

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            text = _page_text(page)

            if _is_report_page(text):
                # Close current claim if open
                if current:
                    current["page_end"] = page_num - 1
                    claims.append(current)
                    current = None
                # Start or extend a report block
                if claims and claims[-1]["type"] == "report":
                    claims[-1]["page_end"] = page_num
                else:
                    claims.append({
                        "label": f"Report (page {page_num})",
                        "page_start": page_num,
                        "page_end": page_num,
                        "type": "report",
                        "info": {},
                    })

            elif _is_claim_start(text):
                # Close previous claim
                if current:
                    current["page_end"] = page_num - 1
                    claims.append(current)

                info = _extract_patient_info(page)
                n = sum(1 for c in claims if c["type"] == "claim") + 1
                patient_label = info.get("patient") or f"Patient {n}"
                bill_label    = info.get("bill_no")  or ""
                label = f"Claim {n} — {patient_label}"
                if bill_label:
                    label += f" (Bill: {bill_label})"

                current = {
                    "label":      label,
                    "page_start": page_num,
                    "page_end":   total,
                    "type":       "claim",
                    "info":       info,
                }
            else:
                # Continuation page — keep extending current claim
                if current is None:
                    current = {
                        "label":      f"Claim 1 (page {page_num})",
                        "page_start": page_num,
                        "page_end":   total,
                        "type":       "claim",
                        "info":       {},
                    }

    if current:
        claims.append(current)

    # If nothing was detected, treat the whole file as one claim
    if not claims:
        claims = [{
            "label": "Claim 1",
            "page_start": 1,
            "page_end": total,
            "type": "claim",
            "info": {},
        }]

    return claims


def extract_line_items_from_pages(pdf_path: Path, page_start: int, page_end: int) -> list[dict]:
    """Extract line items from a specific page range (1-based)."""
    items = []

    if is_text_based(pdf_path):
        with pdfplumber.open(pdf_path) as pdf:
            pages = pdf.pages[page_start - 1: page_end]
            current_section_category = None
            skip_headers = {"description", "qty", "unit price", "amount", "note",
                            "patient name", "date admitted", "ward", "diagnosis"}

            for page in pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            cells = [c.strip() if c else "" for c in row]
                            non_empty = [c for c in cells if c]
                            if not non_empty:
                                continue
                            first = cells[0].lower().rstrip(":") if cells[0] else ""
                            if first in skip_headers:
                                continue
                            if cells[0].strip().endswith(":"):
                                continue
                            rest_empty = all(not c for c in cells[1:])
                            if rest_empty and cells[0] and len(cells[0]) > 3:
                                cat = section_header_to_category(cells[0])
                                if cat:
                                    current_section_category = cat
                                continue
                            if first == "" and any("subtotal" in (c or "").lower() for c in cells):
                                continue

                            date_val = ""
                            cells_no_date = []
                            for cell in cells:
                                if cell and not date_val:
                                    m = DATE_RE.search(cell)
                                    if m and len(cell.strip()) <= 15:
                                        date_val = m.group(0)
                                        continue
                                cells_no_date.append(cell)
                            cells = cells_no_date

                            desc_parts = []
                            amount = ""
                            note = ""
                            if cells[-1] and not looks_like_amount(cells[-1].replace(",", "")):
                                note = cells[-1]
                                cells = cells[:-1]

                            qty_val = ""
                            unit_price = ""
                            numeric_seen = 0
                            for cell in reversed(cells):
                                if not cell:
                                    continue
                                clean = cell.replace(",", "").replace(".", "")
                                is_numeric = looks_like_amount(clean)
                                is_qty = bool(re.match(
                                    r"^\d+(\s*(days?|hrs?|vials?|amps?|bags?|sets?|units?|packs?|"
                                    r"doses?|syringes?|copies|rounds?|visits?|tabs?|caps?))?$",
                                    cell.strip(), re.I))
                                if is_numeric and numeric_seen == 0:
                                    amount = cell; numeric_seen += 1
                                elif is_numeric and numeric_seen == 1:
                                    unit_price = cell; numeric_seen += 1
                                elif is_qty and not qty_val:
                                    qty_val = cell
                                else:
                                    desc_parts.insert(0, cell)

                            description = " ".join(desc_parts).strip()
                            if not description or len(description) <= 2:
                                continue

                            if "non-covered" in note.lower() or "not covered" in note.lower():
                                category = "Not Covered by Insurance"
                            else:
                                item_kw = categorize(description)
                                if item_kw in ("Anaesthetist's Fee", "Professional Fee", "Surgeon's Fee",
                                               "Room & Board", "ICU / Intensive Care", "Operating Room",
                                               "Laboratory", "Radiology / Imaging", "Pharmacy / Medications",
                                               "Not Covered by Insurance"):
                                    category = item_kw
                                elif current_section_category:
                                    category = current_section_category
                                else:
                                    category = item_kw

                            items.append({
                                "description": description,
                                "amount": amount,
                                "note": note,
                                "date": date_val,
                                "raw": " | ".join(non_empty),
                                "category": category,
                            })
                else:
                    text = page.extract_text() or ""
                    for item in parse_lines(text):
                        item["category"] = categorize(item["description"])
                        items.append(item)
    else:
        # Scanned — OCR only the relevant pages
        from pdf2image import convert_from_path as cfp
        imgs = cfp(pdf_path, dpi=300, first_page=page_start, last_page=page_end)
        text = "\n".join(pytesseract.image_to_string(img) for img in imgs)
        for item in parse_lines(text):
            item["category"] = categorize(item["description"])
            items.append(item)

    return items


def extract_line_items(pdf_path: Path) -> list[dict]:
    """
    Extract rows from PDF. Auto-detects text-based vs scanned and uses OCR if needed.
    Uses section headers found in the bill to categorize items accurately.
    Returns list of {"description": str, "amount": str, "raw": str}.
    """
    items = []

    if is_text_based(pdf_path):
        with pdfplumber.open(pdf_path) as pdf:
            current_section_category = None
            skip_headers = {"description", "qty", "unit price", "amount", "note",
                            "patient name", "date admitted", "ward", "diagnosis"}

            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            cells = [c.strip() if c else "" for c in row]
                            non_empty = [c for c in cells if c]
                            if not non_empty:
                                continue

                            first = cells[0].lower().rstrip(":") if cells[0] else ""

                            # Skip column header rows and patient info rows
                            if first in skip_headers:
                                continue
                            # Also skip rows whose first cell ends with ":" (label rows like "Patient Name:")
                            if cells[0].strip().endswith(":"):
                                continue

                            # Detect section header: first cell has text, rest are None/empty
                            rest_empty = all(not c for c in cells[1:])
                            if rest_empty and cells[0] and len(cells[0]) > 3:
                                cat = section_header_to_category(cells[0])
                                if cat:
                                    current_section_category = cat
                                continue

                            # Skip subtotal rows
                            if first == "" and any("subtotal" in (c or "").lower() for c in cells):
                                continue

                            # Pull out date cells FIRST so they don't pollute description
                            date_val = ""
                            cells_no_date = []
                            for cell in cells:
                                if cell and not date_val:
                                    m = DATE_RE.search(cell)
                                    # Accept as a date cell only if it's short (pure date, not description)
                                    if m and len(cell.strip()) <= 15:
                                        date_val = m.group(0)
                                        continue  # remove from cells used for description
                                cells_no_date.append(cell)
                            cells = cells_no_date

                            # Extract note, amount, description from remaining cells
                            desc_parts = []
                            amount = ""
                            note = ""
                            if cells[-1] and not looks_like_amount(cells[-1].replace(",", "")):
                                note = cells[-1]
                                cells = cells[:-1]
                            # Walk cells right-to-left: grab amount, unit price, qty — keep only description
                            qty_val = ""
                            unit_price = ""
                            numeric_seen = 0  # first numeric = amount, second = unit price
                            for cell in reversed(cells):
                                if not cell:
                                    continue
                                clean = cell.replace(",", "").replace(".", "")
                                is_numeric = looks_like_amount(clean)
                                is_qty = bool(re.match(
                                    r"^\d+(\s*(days?|hrs?|vials?|amps?|bags?|sets?|units?|packs?|"
                                    r"doses?|syringes?|copies|rounds?|visits?|tabs?|caps?))?$",
                                    cell.strip(), re.I))
                                if is_numeric and numeric_seen == 0:
                                    amount = cell; numeric_seen += 1
                                elif is_numeric and numeric_seen == 1:
                                    unit_price = cell; numeric_seen += 1  # skip unit price
                                elif is_qty and not qty_val:
                                    qty_val = cell  # skip qty
                                else:
                                    desc_parts.insert(0, cell)
                            description = " ".join(desc_parts).strip()
                            if not description or len(description) <= 2:
                                continue

                            if "non-covered" in note.lower() or "not covered" in note.lower():
                                category = "Not Covered by Insurance"
                            else:
                                item_kw = categorize(description)
                                if item_kw in ("Anaesthetist's Fee", "Professional Fee", "Surgeon's Fee",
                                               "Room & Board", "ICU / Intensive Care", "Operating Room",
                                               "Laboratory", "Radiology / Imaging", "Pharmacy / Medications",
                                               "Not Covered by Insurance"):
                                    category = item_kw
                                elif current_section_category:
                                    category = current_section_category
                                else:
                                    category = item_kw

                            items.append({
                                "description": description,
                                "amount": amount,
                                "note": note,
                                "date": date_val,
                                "raw": " | ".join(non_empty),
                                "category": category,
                            })
                else:
                    text = page.extract_text() or ""
                    for item in parse_lines(text):
                        item["category"] = categorize(item["description"])
                        items.append(item)
    else:
        text = extract_text_from_scanned(pdf_path)
        for item in parse_lines(text):
            item["category"] = categorize(item["description"])
            items.append(item)

    return items


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

def make_border():
    thin = Side(style="thin")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _apply_header_row(ws, headers: list, row: int, fill_color: str = "1F3864"):
    hf = Font(bold=True, color="FFFFFF")
    hfill = PatternFill("solid", fgColor=fill_color)
    border = make_border()
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col)
        cell.value = h
        cell.font = hf
        cell.fill = hfill
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row].height = 18


def write_excel_multi(claims_data: list[dict], out_path: Path):
    """
    Write a multi-claim Excel workbook.
    claims_data: list of {"label": str, "items": list[dict], "type": str}
    Produces:
      - "Index" sheet listing all claims
      - One "Summary" + one "Full Breakdown" sheet per claim
      - Report pages noted but not parsed
    """
    wb = openpyxl.Workbook()
    border = make_border()
    center = Alignment(horizontal="center", vertical="center")

    # ── Index sheet ──────────────────────────────────────────────────
    ws_idx = wb.active
    ws_idx.title = "Index"
    ws_idx.merge_cells("A1:E1")
    t = ws_idx["A1"]
    t.value = "Batch Bill — Claim Index"
    t.font = Font(bold=True, size=14, color="FFFFFF")
    t.fill = PatternFill("solid", fgColor="1F3864")
    t.alignment = center
    ws_idx.row_dimensions[1].height = 28

    _apply_header_row(ws_idx, ["#", "Label", "Type", "Pages", "Total Amount"], 2)
    ws_idx.column_dimensions["A"].width = 4
    ws_idx.column_dimensions["B"].width = 45
    ws_idx.column_dimensions["C"].width = 10
    ws_idx.column_dimensions["D"].width = 12
    ws_idx.column_dimensions["E"].width = 16

    row = 3
    for i, claim in enumerate(claims_data, 1):
        color = "F4CCCC" if claim["type"] == "report" else "D6E4F0"
        total = sum(
            float(it["amount"].replace(",", ""))
            for it in claim.get("items", [])
            if it.get("amount") and it["amount"].replace(",","").replace(".","").isdigit()
        )
        ws_idx.cell(row=row, column=1).value = i
        ws_idx.cell(row=row, column=2).value = claim["label"]
        ws_idx.cell(row=row, column=3).value = claim["type"].capitalize()
        ws_idx.cell(row=row, column=4).value = f"p.{claim.get('page_start','?')}–{claim.get('page_end','?')}"
        ws_idx.cell(row=row, column=5).value = f"{total:,.2f}" if total else "—"
        for col in range(1, 6):
            cell = ws_idx.cell(row=row, column=col)
            cell.fill = PatternFill("solid", fgColor=color)
            cell.border = border
            cell.alignment = Alignment(vertical="center")
        row += 1

    # ── One sheet-pair per claim ─────────────────────────────────────
    for claim in claims_data:
        label = claim["label"][:28]  # Excel sheet name max 31 chars
        items = claim.get("items", [])

        if claim["type"] == "report":
            ws_r = wb.create_sheet(f"{label[:27]}…" if len(label) > 27 else label)
            ws_r.merge_cells("A1:B1")
            c = ws_r["A1"]
            c.value = f"📄 {claim['label']} — Report / Non-bill pages (not parsed)"
            c.font = Font(bold=True, size=11, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="CC0000")
            c.alignment = center
            ws_r.column_dimensions["A"].width = 60
            continue

        if not items:
            continue

        # Summary sheet
        safe = re.sub(r"[\\/*?:\[\]]", "", label)[:28]
        ws_sum = wb.create_sheet(f"{safe} – Sum")
        ws_sum.merge_cells("A1:C1")
        t2 = ws_sum["A1"]
        t2.value = f"{claim['label']} — Summary"
        t2.font = Font(bold=True, size=13, color="FFFFFF")
        t2.fill = PatternFill("solid", fgColor="1F3864")
        t2.alignment = center
        ws_sum.row_dimensions[1].height = 26
        _apply_header_row(ws_sum, ["Category", "Total Amount", "Items"], 2)

        grouped = {cat: [] for cat in CATEGORIES}
        for item in items:
            grouped[item["category"]].append(item)

        grand = 0.0
        r = 3
        for cat, cat_items in grouped.items():
            if not cat_items:
                continue
            color = CATEGORY_COLORS.get(cat, "FFFFFF")
            total = 0.0
            for it in cat_items:
                try: total += float(it["amount"].replace(",", ""))
                except: pass
            grand += total
            ws_sum.cell(row=r, column=1).value = cat
            ws_sum.cell(row=r, column=2).value = f"{total:,.2f}" if total else ""
            ws_sum.cell(row=r, column=3).value = len(cat_items)
            for col in range(1, 4):
                cell = ws_sum.cell(row=r, column=col)
                cell.fill = PatternFill("solid", fgColor=color)
                cell.border = border
                cell.alignment = Alignment(vertical="center")
            r += 1

        ws_sum.cell(row=r, column=1).value = "GRAND TOTAL"
        ws_sum.cell(row=r, column=2).value = f"{grand:,.2f}"
        ws_sum.cell(row=r, column=3).value = len(items)
        for col in range(1, 4):
            cell = ws_sum.cell(row=r, column=col)
            cell.font = Font(bold=True, size=12, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F3864")
            cell.border = border
            cell.alignment = center
        ws_sum.column_dimensions["A"].width = 28
        ws_sum.column_dimensions["B"].width = 18
        ws_sum.column_dimensions["C"].width = 10

        # Full breakdown sheet
        ws_det = wb.create_sheet(f"{safe} – Detail")
        ws_det.merge_cells("A1:F1")
        t3 = ws_det["A1"]
        t3.value = f"{claim['label']} — Full Breakdown"
        t3.font = Font(bold=True, size=13, color="FFFFFF")
        t3.fill = PatternFill("solid", fgColor="1F3864")
        t3.alignment = center
        ws_det.row_dimensions[1].height = 26
        _apply_header_row(ws_det, ["#", "Date", "Category", "Description", "Amount", "Note / Coverage"], 2)

        r = 3
        prev_cat = None
        rn = 1
        for item in items:
            cat = item["category"]
            color = CATEGORY_COLORS.get(cat, "FFFFFF")
            if cat != prev_cat:
                ws_det.merge_cells(f"A{r}:F{r}")
                div = ws_det.cell(row=r, column=1)
                div.value = f"  {cat}"
                div.font = Font(bold=True, size=10)
                div.fill = PatternFill("solid", fgColor=color)
                div.border = border
                ws_det.row_dimensions[r].height = 15
                r += 1
                prev_cat = cat
            ws_det.cell(row=r, column=1).value = rn
            ws_det.cell(row=r, column=2).value = item.get("date", "")
            ws_det.cell(row=r, column=3).value = cat
            ws_det.cell(row=r, column=4).value = item["description"]
            ws_det.cell(row=r, column=5).value = item["amount"]
            note = item.get("note", "")
            ws_det.cell(row=r, column=6).value = note
            if note and "non-covered" in note.lower():
                ws_det.cell(row=r, column=6).font = Font(color="CC0000", bold=True)
            for col in range(1, 7):
                cell = ws_det.cell(row=r, column=col)
                cell.fill = PatternFill("solid", fgColor=color)
                cell.border = border
                cell.alignment = Alignment(vertical="center", wrap_text=(col == 4))
            r += 1
            rn += 1

        ws_det.column_dimensions["A"].width = 5
        ws_det.column_dimensions["B"].width = 14
        ws_det.column_dimensions["C"].width = 24
        ws_det.column_dimensions["D"].width = 50
        ws_det.column_dimensions["E"].width = 14
        ws_det.column_dimensions["F"].width = 20

    wb.save(out_path)
    n_claims = sum(1 for c in claims_data if c["type"] == "claim")
    n_reports = sum(1 for c in claims_data if c["type"] == "report")
    print(f"Saved: {out_path}  ({n_claims} claim(s), {n_reports} report section(s))")


def write_excel(items: list[dict], out_path: Path):
    wb = openpyxl.Workbook()

    # -----------------------------------------------------------------------
    # Sheet 1 — Summary by category
    # -----------------------------------------------------------------------
    ws_sum = wb.active
    ws_sum.title = "Summary"

    border = make_border()
    center = Alignment(horizontal="center", vertical="center")
    total_font = Font(bold=True, italic=True)

    ws_sum.merge_cells("A1:C1")
    t = ws_sum["A1"]
    t.value = "Hospital Bill — Category Summary"
    t.font = Font(bold=True, size=14, color="FFFFFF")
    t.fill = PatternFill("solid", fgColor="1F3864")
    t.alignment = center
    ws_sum.row_dimensions[1].height = 28

    _apply_header_row(ws_sum, ["Category", "Total Amount", "Items"], 2)

    grouped: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
    for item in items:
        grouped[item["category"]].append(item)

    grand_total = 0.0
    current_row = 3
    for category, cat_items in grouped.items():
        if not cat_items:
            continue
        color = CATEGORY_COLORS.get(category, "FFFFFF")
        cat_fill = PatternFill("solid", fgColor=color)
        cat_total = 0.0
        for item in cat_items:
            try:
                cat_total += float(item["amount"].replace(",", ""))
            except (ValueError, AttributeError):
                pass
        grand_total += cat_total

        ws_sum.cell(row=current_row, column=1).value = category
        ws_sum.cell(row=current_row, column=2).value = f"{cat_total:,.2f}" if cat_total else ""
        ws_sum.cell(row=current_row, column=3).value = len(cat_items)
        for col in range(1, 4):
            cell = ws_sum.cell(row=current_row, column=col)
            cell.fill = cat_fill
            cell.border = border
            cell.alignment = Alignment(vertical="center")
        current_row += 1

    # Grand total row
    ws_sum.cell(row=current_row, column=1).value = "GRAND TOTAL"
    ws_sum.cell(row=current_row, column=2).value = f"{grand_total:,.2f}"
    ws_sum.cell(row=current_row, column=3).value = len(items)
    for col in range(1, 4):
        cell = ws_sum.cell(row=current_row, column=col)
        cell.font = Font(bold=True, size=12, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3864")
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    ws_sum.column_dimensions["A"].width = 28
    ws_sum.column_dimensions["B"].width = 18
    ws_sum.column_dimensions["C"].width = 10

    # -----------------------------------------------------------------------
    # Sheet 2 — Full line-by-line breakdown (every item with date)
    # -----------------------------------------------------------------------
    ws_det = wb.create_sheet("Full Breakdown")

    ws_det.merge_cells("A1:F1")
    t2 = ws_det["A1"]
    t2.value = "Hospital Bill — Full Itemized Breakdown"
    t2.font = Font(bold=True, size=14, color="FFFFFF")
    t2.fill = PatternFill("solid", fgColor="1F3864")
    t2.alignment = center
    ws_det.row_dimensions[1].height = 28

    _apply_header_row(ws_det, ["#", "Date", "Category", "Description", "Amount", "Note / Coverage"], 2)

    current_row = 3
    prev_category = None
    row_num = 1
    for item in items:
        category = item["category"]
        color = CATEGORY_COLORS.get(category, "FFFFFF")
        cat_fill = PatternFill("solid", fgColor=color)

        # Insert a category divider when the category changes
        if category != prev_category:
            ws_det.merge_cells(f"A{current_row}:F{current_row}")
            div = ws_det.cell(row=current_row, column=1)
            div.value = f"  {category}"
            div.font = Font(bold=True, size=10)
            div.fill = PatternFill("solid", fgColor=color)
            div.border = border
            ws_det.row_dimensions[current_row].height = 15
            current_row += 1
            prev_category = category

        ws_det.cell(row=current_row, column=1).value = row_num
        ws_det.cell(row=current_row, column=2).value = item.get("date", "")
        ws_det.cell(row=current_row, column=3).value = category
        ws_det.cell(row=current_row, column=4).value = item["description"]
        ws_det.cell(row=current_row, column=5).value = item["amount"]
        note = item.get("note", "")
        ws_det.cell(row=current_row, column=6).value = note
        if note and ("non-covered" in note.lower() or "not covered" in note.lower()):
            ws_det.cell(row=current_row, column=6).font = Font(color="CC0000", bold=True)

        for col in range(1, 7):
            cell = ws_det.cell(row=current_row, column=col)
            cell.fill = cat_fill
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=(col == 4))

        current_row += 1
        row_num += 1

    ws_det.column_dimensions["A"].width = 5
    ws_det.column_dimensions["B"].width = 14
    ws_det.column_dimensions["C"].width = 24
    ws_det.column_dimensions["D"].width = 50
    ws_det.column_dimensions["E"].width = 14
    ws_det.column_dimensions["F"].width = 20

    wb.save(out_path)
    print(f"Saved: {out_path} (2 sheets: Summary + Full Breakdown)")


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

    # Auto-detect batch (multiple claims) vs single bill
    claims = split_into_claims(pdf_path)

    if len(claims) > 1:
        print(f"\nDetected {len(claims)} section(s) in batch PDF:")
        for c in claims:
            print(f"  [{c['type'].upper():6}] p.{c['page_start']}–{c['page_end']}  {c['label']}")

        claims_data = []
        for claim in claims:
            if claim["type"] == "report":
                print(f"\nSkipping report section: {claim['label']}")
                claims_data.append({**claim, "items": []})
                continue
            print(f"\nProcessing: {claim['label']} (pages {claim['page_start']}–{claim['page_end']})...")
            items = extract_line_items_from_pages(pdf_path, claim["page_start"], claim["page_end"])
            for item in items:
                if "category" not in item:
                    item["category"] = categorize(item["description"])
            print(f"  → {len(items)} line items")
            claims_data.append({**claim, "items": items})

        write_excel_multi(claims_data, out_path)

    else:
        # Single bill
        items = extract_line_items(pdf_path)
        if not items:
            print("No line items found. The PDF may be scanned (image-based). Try OCR first.")
            sys.exit(1)
        for item in items:
            if "category" not in item:
                item["category"] = categorize(item["description"])
        from collections import Counter
        counts = Counter(item["category"] for item in items)
        print(f"\nExtracted {len(items)} line item(s):")
        for cat, count in counts.items():
            print(f"  {cat}: {count}")
        write_excel(items, out_path)


if __name__ == "__main__":
    main()
