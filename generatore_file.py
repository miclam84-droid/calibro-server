# generatore_file.py — genera PDF / Excel / Word da contenuto STRUTTURATO.
#
# Principio di onestà (vale per il chiamante, non per questo modulo):
#   questo modulo rende fedelmente ciò che riceve. I NUMERI (es. food cost) devono
#   arrivare già veri (dal listino) o etichettati come stima con la fonte: il modulo
#   non inventa nulla, impagina soltanto. La colonna/provenienza la mette il chiamante.
#
# Modello di contenuto (unificato per PDF e Word) = lista di BLOCCHI:
#   {"tipo": "h1"|"h2"|"p",     "testo": "..."}
#   {"tipo": "tabella", "intestazioni": ["A","B"], "righe": [["1","2"], ...], "nota": "..."}
# Per Excel = lista di FOGLI:
#   {"nome": "Ricette", "intestazioni": [...], "righe": [[...], ...]}

import io
from datetime import datetime

MAX_RIGHE = 5000          # guardia anti-abuso
MAX_BLOCCHI = 400


def _oggi():
    return datetime.now().strftime("%d/%m/%Y")


# ───────────────────────── EXCEL (openpyxl) ─────────────────────────
def genera_excel(titolo, fogli):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    wb.remove(wb.active)
    intest_fill = PatternFill("solid", fgColor="9E4D1C")   # rame
    intest_font = Font(bold=True, color="FFFFFF")
    bordo = Border(*[Side(style="thin", color="DEDED4")] * 4)

    fogli = (fogli or [])[:12]
    if not fogli:
        fogli = [{"nome": "Foglio", "intestazioni": [], "righe": []}]
    for i, f in enumerate(fogli):
        nome = (str(f.get("nome") or f"Foglio {i+1}"))[:31] or f"Foglio {i+1}"
        ws = wb.create_sheet(title=nome)
        intest = [str(x) for x in (f.get("intestazioni") or [])]
        if intest:
            ws.append(intest)
            for c, _ in enumerate(intest, start=1):
                cell = ws.cell(row=1, column=c)
                cell.fill = intest_fill; cell.font = intest_font
                cell.alignment = Alignment(vertical="center")
                cell.border = bordo
        for riga in (f.get("righe") or [])[:MAX_RIGHE]:
            ws.append([("" if v is None else v) for v in riga])
        # larghezza colonne auto (rozza ma utile)
        ncol = max([len(intest)] + [len(r) for r in (f.get("righe") or [])[:200]] + [1])
        for c in range(1, ncol + 1):
            maxlen = 10
            for r in range(1, min(ws.max_row, 200) + 1):
                v = ws.cell(row=r, column=c).value
                if v is not None:
                    maxlen = max(maxlen, len(str(v)))
            ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = min(maxlen + 2, 48)
        ws.freeze_panes = "A2" if intest else None
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return buf


# ───────────────────────── PDF (reportlab) ─────────────────────────
def genera_pdf(titolo, blocchi):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18*mm, bottomMargin=16*mm,
                            leftMargin=16*mm, rightMargin=16*mm, title=str(titolo or "Documento"))
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=18, textColor=colors.HexColor("#17150F"))
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, textColor=colors.HexColor("#9E4D1C"))
    p = ParagraphStyle("p", parent=ss["BodyText"], fontSize=10.5, leading=15)
    nota = ParagraphStyle("nota", parent=ss["BodyText"], fontSize=8.5, textColor=colors.HexColor("#5E5E55"))

    story = [Paragraph(str(titolo or "Documento"), h1),
             Paragraph(f"Matter Bench · {_oggi()}", nota), Spacer(1, 8)]
    for b in (blocchi or [])[:MAX_BLOCCHI]:
        t = (b.get("tipo") or "p").lower()
        if t == "h1":
            story.append(Spacer(1, 6)); story.append(Paragraph(str(b.get("testo", "")), h1))
        elif t == "h2":
            story.append(Spacer(1, 6)); story.append(Paragraph(str(b.get("testo", "")), h2))
        elif t == "tabella":
            intest = [str(x) for x in (b.get("intestazioni") or [])]
            righe = [[str("" if v is None else v) for v in r] for r in (b.get("righe") or [])[:MAX_RIGHE]]
            dati = ([intest] if intest else []) + righe
            if dati:
                tb = Table(dati, repeatRows=1 if intest else 0)
                st = [("FONTSIZE", (0, 0), (-1, -1), 9),
                      ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D4C9")),
                      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                      ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
                if intest:
                    st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3E7DC")),
                           ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
                tb.setStyle(TableStyle(st))
                story.append(tb)
            if b.get("nota"):
                story.append(Paragraph(str(b["nota"]), nota))
            story.append(Spacer(1, 8))
        else:
            story.append(Paragraph(str(b.get("testo", "")), p)); story.append(Spacer(1, 4))
    doc.build(story)
    buf.seek(0)
    return buf


# ───────────────────────── WORD (python-docx) ─────────────────────────
def genera_docx(titolo, blocchi):
    from docx import Document
    from docx.shared import Pt, RGBColor

    d = Document()
    d.add_heading(str(titolo or "Documento"), level=0)
    sub = d.add_paragraph(f"Matter Bench · {_oggi()}")
    sub.runs[0].font.size = Pt(9); sub.runs[0].font.color.rgb = RGBColor(0x5E, 0x5E, 0x55)
    for b in (blocchi or [])[:MAX_BLOCCHI]:
        t = (b.get("tipo") or "p").lower()
        if t == "h1":
            d.add_heading(str(b.get("testo", "")), level=1)
        elif t == "h2":
            d.add_heading(str(b.get("testo", "")), level=2)
        elif t == "tabella":
            intest = [str(x) for x in (b.get("intestazioni") or [])]
            righe = [[str("" if v is None else v) for v in r] for r in (b.get("righe") or [])[:MAX_RIGHE]]
            ncol = max([len(intest)] + [len(r) for r in righe] + [1])
            tab = d.add_table(rows=0, cols=ncol); tab.style = "Light Grid Accent 1"
            if intest:
                cells = tab.add_row().cells
                for i, h in enumerate(intest[:ncol]):
                    cells[i].text = h
            for r in righe:
                cells = tab.add_row().cells
                for i in range(ncol):
                    cells[i].text = r[i] if i < len(r) else ""
            if b.get("nota"):
                n = d.add_paragraph(str(b["nota"])); n.runs[0].font.size = Pt(8.5)
        else:
            d.add_paragraph(str(b.get("testo", "")))
    buf = io.BytesIO()
    d.save(buf); buf.seek(0)
    return buf


# ───────────────────────── dispatcher ─────────────────────────
_MIME = {
    "pdf":  ("application/pdf", "pdf"),
    "excel": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "word": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
}


def genera(tipo, titolo, contenuto):
    """tipo: 'pdf'|'excel'|'word'. contenuto: blocchi (pdf/word) o fogli (excel).
    Ritorna (BytesIO, mimetype, estensione)."""
    tipo = (tipo or "pdf").lower()
    if tipo in ("xlsx", "excel", "xls"):
        return genera_excel(titolo, contenuto), _MIME["excel"][0], "xlsx"
    if tipo in ("docx", "word", "doc"):
        return genera_docx(titolo, contenuto), _MIME["word"][0], "docx"
    return genera_pdf(titolo, contenuto), _MIME["pdf"][0], "pdf"
