"""Generate the synthetic SIH demo dataset: 1 tender + 5 bidder packages.

Planted ground truth (what the engine must catch):
  A Apex Computing Solutions  -> CLEAN (PASS, L1)
  B Brightline Technologies   -> turnover fraud: claims 2.4 Cr, CA cert shows 1.1 Cr avg;
                                 invalid CA membership no. "FCA-0987X4";
                                 malformed PAN "B1KPB5678Q" (FAIL)
  C Crestline Systems         -> shares 2 directors + phone + address + bank account +
                                 submission IP + DSC token with D; price within 0.7% of D
                                 (cover-bidding signal); same PDF author metadata as D;
                                 identical draft sentence with typos shared with D (REVIEW)
  D Deltaforce IT Services    -> collusion with C + MISSING GFR 144(xi) declaration (FAIL)
  E Everest Digital           -> claims Class-I but declares 28% local content (Class-II);
                                 past performance 40L < 75L requirement;
                                 price hint hidden in the technical bid (FAIL)

Tender-level planted patterns:
  - tender_corrigendum.pdf relaxes turnover 1.5 Cr -> 1.0 Cr and EMD 2 L -> 1 L
    after publication (mid-tender tailoring demo)
  - the 5 bid prices form an abnormally tight cluster (CV screen demo)
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, HRFlowable)
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
W, H = A4
styles = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=styles["Normal"], fontSize=10.5, leading=14.5,
                      alignment=TA_JUSTIFY, spaceAfter=6)
H1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=15, leading=18,
                    alignment=TA_CENTER, spaceAfter=4, textColor=colors.HexColor("#0f2a4a"))
H2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12.5, leading=15,
                    spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#0f2a4a"))
SMALL = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, leading=12,
                       textColor=colors.HexColor("#444444"))
CELL = ParagraphStyle("cell", parent=styles["Normal"], fontSize=10, leading=13)
CELLC = ParagraphStyle("cellc", parent=CELL, alignment=TA_CENTER)
HDRC = ParagraphStyle("hdrc", parent=CELL, alignment=TA_CENTER, textColor=colors.white,
                      fontName="Helvetica-Bold")


def doc(path, author=None):
    d = SimpleDocTemplate(path, pagesize=A4,
                          leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=18 * mm, bottomMargin=18 * mm,
                          author=author or "SatyaBid Synthetic Data Generator")
    return d


def styled_table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2a4a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def money(n):
    return f"Rs. {n:,.0f}/-"


# ---------------------------------------------------------------- tender ---
def make_tender():
    d = doc(os.path.join(BASE, "tender.pdf"), author="GeM Portal (synthetic)")
    s = [Paragraph("GOVERNMENT E-MARKETPLACE (GeM) — BID DOCUMENT", H1),
         Paragraph("Bid Number: GEM/2026/B/6123457 &nbsp;&nbsp;|&nbsp;&nbsp; "
                   "Buyer: Chennai Petroleum Corporation Ltd. (CPCL)", SMALL),
         HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f2a4a")),
         Spacer(1, 6),
         Paragraph("Supply, Installation and Commissioning of 500 Nos. Desktop Computers "
                   "with 3-Year Onsite Warranty", H2),
         Paragraph("1. Estimated bid value: <b>Rs. 4,50,00,000/-</b> (Rupees Four Crore "
                   "Fifty Lakh only).", BODY),
         Paragraph("2. <b>Earnest Money Deposit (EMD): Rs. 2,00,000/-.</b> Micro and Small "
                   "Enterprises (MSEs) and DPIIT-recognised Startups holding a valid Udyam "
                   "Registration Certificate are exempted from EMD submission.", BODY),
         Paragraph("3. <b>Minimum average annual turnover</b> of the bidder for the last "
                   "three financial years (FY 2022-23, 2023-24, 2024-25) shall be "
                   "<b>Rs. 1,50,00,000/- (Rupees One Crore Fifty Lakh)</b>, duly certified "
                   "by a practicing Chartered Accountant with valid ICAI membership number.",
                   BODY),
         Paragraph("4. <b>Past performance:</b> the bidder must have successfully supplied "
                   "similar goods (desktop computers / workstations) of cumulative order "
                   "value not less than <b>Rs. 75,00,000/-</b> to any Central/State "
                   "Government organisation or Public Sector Undertaking in the last three "
                   "years. Copies of purchase orders and completion certificates must be "
                   "enclosed.", BODY),
         Paragraph("5. <b>Make in India (DPIIT):</b> In line with the Public Procurement "
                   "(Preference to Make in India) Order 2017, purchase preference shall apply. "
                   "Bidders claiming <b>Class-I Local Supplier</b> status must declare local "
                   "content of <b>50% or more</b>, certified as per the Order. Class-II "
                   "suppliers (local content more than 20% but less than 50%) are eligible "
                   "to participate but shall not receive purchase preference.", BODY),
         Paragraph("6. <b>GFR Rule 144(xi):</b> Every bidder must submit a declaration that "
                   "it is not from a country sharing a land border with India, OR that it is "
                   "registered with the Competent Authority (DPIIT) as required under Rule "
                   "144(xi) of the General Financial Rules 2017. <b>Bids without this "
                   "declaration shall be summarily rejected.</b>", BODY),
         Paragraph("7. Delivery, installation and commissioning at all designated CPCL "
                   "sites within <b>45 days</b> of purchase order. Three-year comprehensive "
                   "onsite warranty is mandatory.", BODY),
         Paragraph("8. Two-cover system: Cover 1 (Technical Bid) and Cover 2 (Financial "
                   "Bid) shall be evaluated independently. The financial bids of only "
                   "technically responsive bidders shall be opened.", BODY),
         ]
    d.build(s)
    print("tender.pdf written")


# ---------------------------------------------------------------- bidders ---
BIDDERS = {
    "A": dict(name="Apex Computing Solutions", city="Chennai",
              directors=[("Rajesh Menon", "Managing Partner"),
                         ("Priya Nair", "Partner")],
              phone="98470-11223", address="14, Guindy Industrial Estate, Chennai 600032",
              pan="AAKCA1234F", gstin="33AAKCA1234F1Z5",
              email="bids@apexcomputing.in", bank="50200011223344",
              ip="49.205.113.7", dsc="eMudhra Token #EM-10293 (Rajesh Menon)",
              turnover_claim="Rs. 2,80,00,000/-", turnover_rows=[
                  ("FY 2024-25", "2,60,00,000"), ("FY 2023-24", "2,90,00,000"),
                  ("FY 2022-23", "3,00,00,000")],
              ca_name="R. Venkatesh", ca_no="FCA-023418",
              local_pct=62, local_class="Class-I Local Supplier",
              has_144xi=True, past_perf="Rs. 1,10,00,000/-",
              past_rows=[("PO/2023/114", "IOCL", "Rs. 68,00,000/-"),
                         ("PO/2024/089", "BHEL", "Rs. 42,00,000/-")],
              price=43200000, emd="Enclosed: DD No. 884512 dated 12-09-2026",
              author="Apex-Office-PC"),
    "B": dict(name="Brightline Technologies", city="Bengaluru",
              directors=[("Suresh Iyer", "Proprietor")],
              phone="98111-22334", address="22, HSR Layout Sector 2, Bengaluru 560102",
              pan="B1KPB5678Q", gstin="29BBKPB5678Q1Z2",
              email="brightline.tech@gmail.com", bank="50200099887700",
              ip="157.34.210.9", dsc="eMudhra Token #EM-44501 (Suresh Iyer)",
              turnover_claim="Rs. 2,40,00,000/-", turnover_rows=[
                  ("FY 2024-25", "1,00,00,000"), ("FY 2023-24", "1,20,00,000"),
                  ("FY 2022-23", "1,10,00,000")],
              ca_name="D. Kulkarni", ca_no="FCA-0987X4",
              local_pct=58, local_class="Class-I Local Supplier",
              has_144xi=True, past_perf="Rs. 82,00,000/-",
              past_rows=[("PO/2024/301", "HAL", "Rs. 82,00,000/-")],
              price=45500000, emd="Enclosed: DD No. 771203 dated 10-09-2026",
              author="Brightline-Laptop"),
    "C": dict(name="Crestline Systems", city="Mumbai",
              directors=[("Vikram Shah", "Director"), ("Anita Desai", "Director"),
                         ("Rohan Kulkarni", "Director")],
              phone="98200-44556", address="8, Andheri MIDC, Mumbai 400093",
              pan="AAKCC8899R", gstin="27AAKCC8899R1Z3",
              email="tenders@crestlinesys.com", bank="50200099887711",
              ip="103.21.44.18", dsc="eMudhra Token #EM-88412 (Vikram Shah)",
              turnover_claim="Rs. 2,10,00,000/-", turnover_rows=[
                  ("FY 2024-25", "2,00,00,000"), ("FY 2023-24", "2,10,00,000"),
                  ("FY 2022-23", "2,20,00,000")],
              ca_name="P. Bhatt", ca_no="ACA-117204",
              local_pct=55, local_class="Class-I Local Supplier",
              has_144xi=True, past_perf="Rs. 90,00,000/-",
              past_rows=[("PO/2023/512", "ONGC", "Rs. 90,00,000/-")],
              price=44100000, emd="Enclosed: DD No. 550981 dated 11-09-2026",
              author="Crestline-PC-03",
              extra_para="We have carefully perused the tender document and "
                         "unconditionally accept all terms and conditions "
                         "stipulated theirin without any devation whatsoever.",
              # ML ground truth: same draft, paraphrased — exact sentence
              # matching misses this; TF-IDF paraphrase screen must catch it.
              extra_para2="Our organisation possesses adequate technical "
                         "manpower and infrastructure to complete the entire "
                         "supply within the stipulated delivery period."),
    "D": dict(name="Deltaforce IT Services", city="Mumbai",
              directors=[("Vikram Shah", "Director"), ("Anita Desai", "Director"),
                         ("Farhan Sheikh", "Director")],
              phone="98200-44556", address="8, Andheri MIDC, Mumbai 400093",
              pan="AAKCD9900S", gstin="27AAKCD9900S1Z4",
              email="info@deltaforceit.in", bank="50200099887711",
              ip="103.21.44.18", dsc="eMudhra Token #EM-88412 (Vikram Shah)",
              turnover_claim="Rs. 1,90,00,000/-", turnover_rows=[
                  ("FY 2024-25", "1,80,00,000"), ("FY 2023-24", "1,90,00,000"),
                  ("FY 2022-23", "2,00,00,000")],
              ca_name="P. Bhatt", ca_no="ACA-117204",
              local_pct=52, local_class="Class-I Local Supplier",
              has_144xi=False, past_perf="Rs. 78,00,000/-",
              past_rows=[("PO/2024/118", "BPCL", "Rs. 78,00,000/-")],
              price=44400000, emd="Enclosed: DD No. 550982 dated 11-09-2026",
              author="Crestline-PC-03",
              extra_para="We have carefully perused the tender document and "
                         "unconditionally accept all terms and conditions "
                         "stipulated theirin without any devation whatsoever.",
              # ML ground truth: same draft as C, paraphrased.
              extra_para2="Our company has adequate technical manpower and "
                         "infrastructure to execute the entire supply within "
                         "the stipulated delivery schedule."),
    "E": dict(name="Everest Digital", city="Pune",
              directors=[("Kavita Rao", "Partner"), ("Deepak Joshi", "Partner")],
              phone="98333-77889", address="5, Hinjewadi Phase 1, Pune 411057",
              pan="AAKCE3344T", gstin="27AAKCE3344T1Z6",
              email="everest.digital@yahoo.in", bank="50200055443322",
              ip="103.88.71.203", dsc="Capricorn Token #CP-20981 (Kavita Rao)",
              turnover_claim="Rs. 2,20,00,000/-", turnover_rows=[
                  ("FY 2024-25", "2,10,00,000"), ("FY 2023-24", "2,20,00,000"),
                  ("FY 2022-23", "2,30,00,000")],
              ca_name="S. Patil", ca_no="FCA-066531",
              local_pct=28, local_class="Class-I Local Supplier",
              has_144xi=True, past_perf="Rs. 40,00,000/-",
              past_rows=[("PO/2024/077", "NHAI", "Rs. 40,00,000/-")],
              price=46100000, emd="Enclosed: DD No. 309911 dated 09-09-2026",
              author="Everest-PC-01",
              price_hint=" Our commercial offer works out to approximately "
                         "Rs. 4,61,00,000/- for the complete scope of supply."),
}


def make_bidder(key, b):
    path = os.path.join(BASE, "bids", f"bidder_{key}_{b['name'].lower().replace(' ', '_')}.pdf")
    d = doc(path, author=b["author"])
    P = lambda t, st=BODY: Paragraph(t, st)
    s = [P(f"<b>TECHNICAL BID — COVER 1</b><br/>Bid No. GEM/2026/B/6123457<br/>"
           f"Bidder: <b>{b['name']}</b>, {b['city']}", H1),
         HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f2a4a")),
         Spacer(1, 4),
         P("<b>1. Covering letter.</b> We hereby submit our technical bid for the subject "
           "tender. Our average annual turnover for the last three financial years is "
           f"<b>{b['turnover_claim']}</b>, as certified by our Chartered Accountant. "
           f"We enclose Earnest Money Deposit. {b['emd']}.{b.get('price_hint', '')}",
           BODY),
         ] + ([P(b["extra_para"], BODY)] if b.get("extra_para") else []) \
           + ([P(b["extra_para2"], BODY)] if b.get("extra_para2") else []) + [
         P("<b>2. Bidder particulars.</b>", H2),
         styled_table(
             [[Paragraph("<b>Field</b>", HDRC), Paragraph("<b>Details</b>", HDRC)],
              [P("Legal name", CELL), P(b["name"], CELL)],
              [P("Registered address", CELL), P(b["address"], CELL)],
              [P("Contact phone", CELL), P(b["phone"], CELL)],
              [P("PAN", CELL), P(b["pan"], CELL)],
              [P("GSTIN", CELL), P(b["gstin"], CELL)],
              [P("Email", CELL), P(b["email"], CELL)],
              [P("Bank A/c", CELL), P(b["bank"], CELL)],
              [P("Submission IP", CELL), P(b["ip"], CELL)],
              [P("DSC token", CELL), P(b["dsc"], CELL)],
              [P("Directors / Partners", CELL),
               P("<br/>".join(f"{n} ({r})" for n, r in b["directors"]), CELL)]],
             [55 * mm, 115 * mm]),
         P("<b>3. Chartered Accountant's turnover certificate.</b> This is to certify that "
           f"M/s {b['name']}, {b['city']} has achieved the following turnover from IT "
           "hardware supply business:", BODY),
         styled_table(
             [[Paragraph("<b>Financial year</b>", HDRC),
               Paragraph("<b>Annual turnover (Rs.)</b>", HDRC)]]
             + [[P(fy, CELLC), P(val, CELLC)] for fy, val in b["turnover_rows"]],
             [85 * mm, 85 * mm]),
         P(f"Certified by: <b>{b['ca_name']}</b>, Chartered Accountant, "
           f"ICAI Membership No. <b>{b['ca_no']}</b>. UDIN: 26023418AAAB1234. "
           "Date: 05-09-2026.", BODY),
         P("<b>4. Make in India — local content declaration (DPIIT).</b> We declare that "
           f"the local content in the offered desktop computers is <b>{b['local_pct']}%"
           f"</b>. We claim status of <b>{b['local_class']}</b> under the Public "
           "Procurement (Preference to Make in India) Order 2017.", BODY),
         ]
    if b["has_144xi"]:
        s.append(P("<b>5. Declaration under GFR Rule 144(xi).</b> We hereby declare that we "
                   "are not from a country sharing a land border with India as defined "
                   "under Rule 144(xi) of the General Financial Rules 2017, and are "
                   "eligible to participate in this procurement.", BODY))
    else:
        s.append(P("<b>5. Declaration under GFR Rule 144(xi).</b> <i>[No declaration "
                   "furnished]</i>", BODY))
    s += [P("<b>6. Past performance.</b> Cumulative value of similar supplies to "
            f"Government/PSU buyers in the last three years: <b>{b['past_perf']}</b>.",
            BODY),
          styled_table(
              [[Paragraph("<b>Purchase order</b>", HDRC),
                Paragraph("<b>Buyer</b>", HDRC),
                Paragraph("<b>Value</b>", HDRC)]]
              + [[P(po, CELLC), P(buyer, CELLC), P(val, CELLC)]
                 for po, buyer, val in b["past_rows"]],
              [55 * mm, 60 * mm, 55 * mm]),
          P("<b>7. Financial bid — Cover 2 (summary).</b> Our total quoted price for "
            "supply, installation and commissioning of 500 desktop computers with 3-year "
            f"onsite warranty is <b>{money(b['price'])}</b>. Detailed BOQ enclosed in "
            "Cover 2.", BODY),
          Spacer(1, 12),
          P(f"Authorised signatory: {b['directors'][0][0]}<br/>Date: 13-09-2026<br/>"
            f"Place: {b['city']}", SMALL)]
    d.build(s)
    print(f"bidder_{key} written")


# ------------------------------------------------------- corrigendum ---
def make_corrigendum():
    """A post-publication amendment that RELAXES eligibility — the classic
    mid-tender tailoring pattern the tender-integrity module must catch."""
    d = doc(os.path.join(BASE, "tender_corrigendum.pdf"),
            author="GeM Portal (synthetic)")
    s = [Paragraph("GOVERNMENT E-MARKETPLACE (GeM) — CORRIGENDUM 1", H1),
         Paragraph("Bid Number: GEM/2026/B/6123457 &nbsp;&nbsp;|&nbsp;&nbsp; "
                   "Issued: 18-09-2026 (after bid submission opened)", SMALL),
         HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f2a4a")),
         Spacer(1, 6),
         Paragraph("The following clauses of the bid document dated 01-09-2026 "
                   "stand amended:", BODY),
         Paragraph("2. <b>Earnest Money Deposit (EMD): Rs. 1,00,000/-.</b> "
                   "Micro and Small Enterprises (MSEs) and DPIIT-recognised "
                   "Startups holding a valid Udyam Registration Certificate "
                   "are exempted from EMD submission.", BODY),
         Paragraph("3. <b>Minimum average annual turnover</b> of the bidder for the last "
                   "three financial years (FY 2022-23, 2023-24, 2024-25) shall be "
                   "<b>Rs. 1,00,00,000/- (Rupees One Crore)</b>, duly certified "
                   "by a practicing Chartered Accountant with valid ICAI membership number.",
                   BODY),
         Paragraph("All other terms and conditions of the original bid document "
                   "remain unchanged.", BODY)]
    d.build(s)
    print("tender_corrigendum.pdf written")


if __name__ == "__main__":
    make_tender()
    make_corrigendum()
    for k, b in BIDDERS.items():
        make_bidder(k, b)
    print("dataset complete:", BASE)
