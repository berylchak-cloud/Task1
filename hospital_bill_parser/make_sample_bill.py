#!/usr/bin/env python3
"""Generates a complex sample hospital bill PDF for testing."""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from pathlib import Path

OUT = Path(__file__).parent / "sample_hospital_bill.pdf"

LINE_ITEMS = [
    # (Description, Qty, Unit Price, Amount, Note)
    ("ROOM & BED CHARGES", None, None, None, ""),
    ("Standard Ward Accommodation (Day 1-3)",       "3 days",  "3,200.00",  "9,600.00", ""),
    ("Single Room Upgrade – Patient Request",        "2 days",  "1,800.00",  "3,600.00", "Non-covered"),
    ("Nursing Care – General Ward",                  "3 days",    "850.00",  "2,550.00", ""),
    ("Isolation Room Surcharge",                     "1 day",   "2,100.00",  "2,100.00", ""),

    ("OPERATING THEATRE", None, None, None, ""),
    ("Operating Room Usage Fee – 4 hrs",             "4 hrs",   "5,500.00", "22,000.00", ""),
    ("Surgical Supplies & Consumables",              "1 set",   "4,320.00",  "4,320.00", ""),
    ("Sterile Draping Pack",                         "2 packs",   "480.00",    "960.00", ""),
    ("Intra-operative Cell Salvage",                 "1 unit",  "3,100.00",  "3,100.00", ""),
    ("Post-Operative Recovery Room – 2 hrs",         "2 hrs",     "900.00",  "1,800.00", ""),

    ("SURGEON & PROFESSIONAL FEES", None, None, None, ""),
    ("Dr. A. Reyes – Primary Surgeon Fee",           "1",      "18,500.00", "18,500.00", ""),
    ("Dr. M. Santos – Assistant Surgeon",            "1",       "4,600.00",  "4,600.00", ""),
    ("Dr. L. Cruz – Anaesthetist Fee",               "4 hrs",   "3,200.00", "12,800.00", ""),
    ("Anaesthesia Drugs & Agents",                   "1 set",   "2,750.00",  "2,750.00", ""),
    ("Dr. J. Tan – Attending Physician (Day 1-3)",   "3 visits",  "800.00",  "2,400.00", ""),
    ("Dr. J. Tan – Ward Round Consultation",         "5 rounds",  "350.00",  "1,750.00", ""),
    ("Dr. P. Lim – Cardiologist Referral",           "1",       "2,200.00",  "2,200.00", ""),
    ("Dr. F. Wong – Radiologist Read Fee",           "1",         "900.00",    "900.00", ""),

    ("DIAGNOSTIC & LABORATORY", None, None, None, ""),
    ("Complete Blood Count (CBC)",                   "2",         "380.00",    "760.00", ""),
    ("Comprehensive Metabolic Panel",                "1",         "520.00",    "520.00", ""),
    ("Arterial Blood Gas (ABG)",                     "3",         "290.00",    "870.00", ""),
    ("Coagulation Profile (PT/APTT/INR)",            "1",         "650.00",    "650.00", ""),
    ("Blood Culture x2 Sets",                        "2",         "480.00",    "960.00", ""),
    ("CT Scan – Abdomen & Pelvis w/ Contrast",       "1",       "4,800.00",  "4,800.00", ""),
    ("Chest X-Ray (PA View)",                        "2",         "320.00",    "640.00", ""),
    ("Ultrasound – Whole Abdomen",                   "1",       "1,200.00",  "1,200.00", ""),
    ("ECG – 12 Lead",                                "2",         "180.00",    "360.00", ""),
    ("Histopathology – Tissue Biopsy",               "1",       "2,600.00",  "2,600.00", ""),

    ("PHARMACY & MEDICATIONS", None, None, None, ""),
    ("IV Fluids – Normal Saline 0.9% x 10 bags",    "10",         "85.00",    "850.00", ""),
    ("Cefazolin 1g IV (Pre-op Prophylaxis)",         "3 vials",   "210.00",    "630.00", ""),
    ("Metronidazole 500mg IV",                       "6 vials",   "145.00",    "870.00", ""),
    ("Morphine Sulfate 10mg",                        "5 amps",    "190.00",    "950.00", ""),
    ("Ondansetron 8mg IV",                           "4 amps",     "95.00",    "380.00", ""),
    ("Pantoprazole 40mg IV",                         "3 vials",   "220.00",    "660.00", ""),
    ("Enoxaparin 40mg SC (DVT Prophylaxis)",         "3 syringes","310.00",    "930.00", ""),
    ("Paracetamol 1g IV",                            "6 bags",     "75.00",    "450.00", ""),
    ("Experimental Biologic Agent – XB-7",           "1 dose",  "9,500.00",  "9,500.00", "Non-covered"),

    ("MISCELLANEOUS & NON-COVERED", None, None, None, ""),
    ("Hospital TV & Cable – 3 days",                 "3 days",    "150.00",    "450.00", "Non-covered"),
    ("WiFi Internet Access – 3 days",                "3 days",     "80.00",    "240.00", "Non-covered"),
    ("Guest Meal Tray x4",                           "4",          "95.00",    "380.00", "Non-covered"),
    ("Patient Comfort Kit (Toiletries)",             "1",         "350.00",    "350.00", "Non-covered"),
    ("Take-Home Medications (Retail)",               "1 set",   "1,240.00",  "1,240.00", "Non-covered"),
    ("Medical Certificate / Discharge Summary",      "2 copies",   "200.00",   "400.00", ""),
    ("Ambulance Transfer Fee",                       "1",       "1,800.00",  "1,800.00", ""),
    ("Wheelchair Rental",                            "2 days",    "120.00",    "240.00", ""),
]

SECTION_TOTALS = {
    "ROOM & BED CHARGES":           17_850.00,
    "OPERATING THEATRE":            32_180.00,
    "SURGEON & PROFESSIONAL FEES":  45_900.00,
    "DIAGNOSTIC & LABORATORY":      13_360.00,
    "PHARMACY & MEDICATIONS":       16_220.00,
    "MISCELLANEOUS & NON-COVERED":   5_100.00,
}
GRAND_TOTAL = sum(SECTION_TOTALS.values())


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    story = []

    # Header
    header_style = ParagraphStyle("header", fontSize=16, fontName="Helvetica-Bold",
                                  alignment=TA_CENTER, textColor=colors.HexColor("#1F3864"))
    sub_style = ParagraphStyle("sub", fontSize=9, alignment=TA_CENTER, textColor=colors.grey)
    normal = ParagraphStyle("n", fontSize=8, fontName="Helvetica")
    right = ParagraphStyle("r", fontSize=8, alignment=TA_RIGHT)

    story.append(Paragraph("METROPOLITAN GENERAL HOSPITAL", header_style))
    story.append(Paragraph("123 Medical Drive, Cityville | Tel: (02) 8000-1234 | www.metrogen.hospital", sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1F3864")))
    story.append(Spacer(1, 4*mm))

    # Patient info table
    info = [
        ["Patient Name:", "DELA CRUZ, JUAN M.",   "Bill No.:",      "MGH-2024-087341"],
        ["Date Admitted:", "10 November 2024",     "Date Discharged:", "13 November 2024"],
        ["Ward:",         "Surgical Ward 3B",      "Attending Physician:", "Dr. J. Tan, MD"],
        ["Diagnosis:",    "Acute Appendicitis –\nLaparoscopic Appendectomy", "HMO / Insurer:", "PhilHealth + MediShield"],
    ]
    info_table = Table(info, colWidths=[35*mm, 65*mm, 42*mm, 48*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",  (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 8),
        ("VALIGN",    (0,0), (-1,-1), "TOP"),
        ("GRID",      (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("BACKGROUND",(0,0), (-1,-1), colors.HexColor("#F0F4FA")),
        ("PADDING",   (0,0), (-1,-1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5*mm))

    # Itemized charges
    story.append(Paragraph("ITEMIZED STATEMENT OF CHARGES", ParagraphStyle(
        "sec", fontSize=11, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1F3864"), alignment=TA_CENTER)))
    story.append(Spacer(1, 3*mm))

    col_widths = [85*mm, 20*mm, 25*mm, 25*mm, 25*mm]
    header_row = [
        Paragraph("<b>Description</b>", normal),
        Paragraph("<b>Qty</b>", ParagraphStyle("c", fontSize=8, alignment=TA_CENTER)),
        Paragraph("<b>Unit Price</b>", ParagraphStyle("c2", fontSize=8, alignment=TA_RIGHT)),
        Paragraph("<b>Amount</b>", ParagraphStyle("c3", fontSize=8, alignment=TA_RIGHT)),
        Paragraph("<b>Note</b>", ParagraphStyle("c4", fontSize=8, alignment=TA_CENTER)),
    ]
    rows = [header_row]
    style_cmds = [
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F3864")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ("PADDING",    (0,0), (-1,-1), 3),
    ]

    row_idx = 1
    section_colors = [
        "#D6E4F0", "#FCE4D6", "#E2EFDA", "#FFF2CC", "#EAD1DC", "#F4CCCC"
    ]
    sec_color_idx = 0

    for item in LINE_ITEMS:
        desc, qty, unit, amt, note = item
        if qty is None:
            # Section header
            sc = section_colors[sec_color_idx % len(section_colors)]
            sec_color_idx += 1
            row = [Paragraph(f"<b>{desc}</b>", ParagraphStyle(
                "sh", fontSize=8.5, fontName="Helvetica-Bold")), "", "", "", ""]
            rows.append(row)
            style_cmds += [
                ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor(sc)),
                ("SPAN",       (0, row_idx), (-1, row_idx)),
                ("FONTNAME",   (0, row_idx), (-1, row_idx), "Helvetica-Bold"),
            ]
        else:
            note_color = colors.HexColor("#CC0000") if note == "Non-covered" else colors.black
            row = [
                Paragraph(desc, normal),
                Paragraph(qty, ParagraphStyle("qc", fontSize=8, alignment=TA_CENTER)),
                Paragraph(unit, ParagraphStyle("ur", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(amt,  ParagraphStyle("ar", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(f'<font color="red">{note}</font>' if note else "", ParagraphStyle(
                    "nc", fontSize=7, alignment=TA_CENTER)),
            ]
            rows.append(row)
            if note == "Non-covered":
                style_cmds.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), colors.red))
        row_idx += 1

    # Section subtotal rows
    for sec, total in SECTION_TOTALS.items():
        row = ["", "", Paragraph("<b>Subtotal</b>", ParagraphStyle("st", fontSize=8, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
               Paragraph(f"<b>{total:,.2f}</b>", ParagraphStyle("sa", fontSize=8, fontName="Helvetica-Bold", alignment=TA_RIGHT)), ""]
        rows.append(row)
        style_cmds += [
            ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#E8EDF5")),
            ("FONTNAME",   (0, row_idx), (-1, row_idx), "Helvetica-Bold"),
        ]
        row_idx += 1

    charges_table = Table(rows, colWidths=col_widths, repeatRows=1)
    charges_table.setStyle(TableStyle(style_cmds))
    story.append(charges_table)
    story.append(Spacer(1, 5*mm))

    # Grand total
    grand_row = [["", "", "GRAND TOTAL", f"PHP {GRAND_TOTAL:,.2f}", ""]]
    gt = Table(grand_row, colWidths=col_widths)
    gt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#1F3864")),
        ("TEXTCOLOR",  (0,0), (-1,-1), colors.white),
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 10),
        ("ALIGN",      (2,0), (2,0), "RIGHT"),
        ("ALIGN",      (3,0), (3,0), "RIGHT"),
        ("PADDING",    (0,0), (-1,-1), 5),
    ]))
    story.append(gt)
    story.append(Spacer(1, 5*mm))

    # Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        "<i>* Items marked 'Non-covered' are not reimbursable under standard medical insurance plans. "
        "Please verify with your HMO/insurer. This bill is for informational purposes only.</i>",
        ParagraphStyle("foot", fontSize=7, textColor=colors.grey)))

    doc.build(story)
    print(f"Created: {OUT}")


if __name__ == "__main__":
    build()
