"""Génération homogène de reçus PDF certifiés et lisibles sur téléphone."""

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from commerce.branding import COULEUR_APPLICATION, NOM_APPLICATION

COULEUR_ACCENT = "#D59A35"
COULEUR_TEXTE = "#1F3144"
COULEUR_DOUCE = "#F3F7F5"
COULEUR_LIGNE = "#DCE6E1"


def _texte(valeur):
    return escape(str(valeur if valeur not in (None, "") else "—"))


def _montant(valeur):
    return f"{Decimal(valeur or 0):,.0f}".replace(",", " ") + " FCFA"


def _date(valeur):
    return valeur.strftime("%d/%m/%Y à %H:%M") if valeur else "—"


def _creer_qr(url):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    tampon = BytesIO()
    qr.make_image(fill_color=COULEUR_TEXTE, back_color="white").save(tampon, format="PNG")
    tampon.seek(0)
    return tampon


def _logo_application_pdf():
    """Charge le wordmark embarqué dans l'image backend, ou depuis le dépôt en local."""
    logo_image = Path(__file__).resolve().parents[3] / "frontend" / "public" / "macdios-wordmark.png"
    logo_embarque = Path(__file__).resolve().parents[2] / "commerce" / "macdios-wordmark.png"
    for chemin in (logo_embarque, logo_image):
        try:
            return chemin.read_bytes()
        except OSError:
            continue
    return None


def construire_recu_certifie(
    *, titre, sous_titre, lignes, montant_principal, code, url_qr, date_generation,
    logo_proprietaire=None, initiales_proprietaire="N",
):
    """Compose un reçu A4 avec en-tête, détail, montant et panneau QR vérifiable."""
    tampon = BytesIO()
    largeur_page, _ = A4
    document = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=21 * mm,
        title=f"{titre} - {NOM_APPLICATION}",
        author=NOM_APPLICATION,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="RecuTitre", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=23, leading=27, textColor=colors.HexColor(COULEUR_TEXTE),
        alignment=TA_LEFT, spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name="RecuSousTitre", parent=styles["Normal"], fontSize=10,
        leading=15, textColor=colors.HexColor("#687A76"),
    ))
    styles.add(ParagraphStyle(
        name="RecuMarque", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=15, leading=18, textColor=colors.HexColor(COULEUR_APPLICATION),
    ))
    styles.add(ParagraphStyle(
        name="RecuMonogramme", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=18, textColor=colors.white, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="RecuLabel", parent=styles["Normal"], fontSize=9,
        leading=13, textColor=colors.HexColor("#71817C"),
    ))
    styles.add(ParagraphStyle(
        name="RecuValeur", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=14, textColor=colors.HexColor(COULEUR_TEXTE),
    ))
    styles.add(ParagraphStyle(
        name="RecuMontant", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=21, leading=25, textColor=colors.HexColor(COULEUR_TEXTE),
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name="RecuCentre", parent=styles["Normal"], fontSize=8,
        leading=11, textColor=colors.HexColor("#687A76"), alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="RecuCode", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=8, leading=11, textColor=colors.HexColor(COULEUR_TEXTE), alignment=TA_CENTER,
    ))

    logo_application = _logo_application_pdf()
    visuel_application = (
        Image(BytesIO(logo_application), width=62 * mm, height=15 * mm, kind="proportional")
        if logo_application else Paragraph(_texte(NOM_APPLICATION), styles["RecuMarque"])
    )
    if logo_proprietaire:
        visuel_commercant = Image(BytesIO(logo_proprietaire), width=16 * mm, height=16 * mm, kind="proportional")
    else:
        visuel_commercant = Table(
            [[Paragraph(_texte(initiales_proprietaire), styles["RecuMonogramme"])]],
            colWidths=[16 * mm], rowHeights=[16 * mm],
        )
        visuel_commercant.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COULEUR_APPLICATION)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
    marque = Table([[
        visuel_application,
        Paragraph("REÇU CERTIFIÉ", ParagraphStyle(
            "RecuEtiquette", parent=styles["RecuCentre"], fontName="Helvetica-Bold",
            textColor=colors.HexColor(COULEUR_APPLICATION), alignment=TA_CENTER,
        )),
        visuel_commercant,
    ]], colWidths=[64 * mm, 89 * mm, 19 * mm])
    marque.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, colors.HexColor(COULEUR_LIGNE)),
    ]))

    details = []
    for libelle, valeur in lignes:
        details.append([
            Paragraph(_texte(libelle), styles["RecuLabel"]),
            Paragraph(_texte(valeur), styles["RecuValeur"]),
        ])
    table_details = Table(details, colWidths=[48 * mm, 124 * mm], hAlign="LEFT")
    table_details.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor(COULEUR_DOUCE)]),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(COULEUR_LIGNE)),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor(COULEUR_LIGNE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))

    total = Table([[
        Paragraph("MONTANT", styles["RecuLabel"]),
        Paragraph(_texte(_montant(montant_principal)), styles["RecuMontant"]),
    ]], colWidths=[48 * mm, 124 * mm])
    total.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBF7EE")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(COULEUR_ACCENT)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
    ]))

    qr_image = Image(_creer_qr(url_qr), width=34 * mm, height=34 * mm)
    panneau_qr = Table([[
        qr_image,
        [
            Paragraph(f"<b>Document certifié {_texte(NOM_APPLICATION)}</b>", styles["RecuValeur"]),
            Spacer(1, 2 * mm),
            Paragraph("Scannez ce code avec l’appareil photo de votre téléphone pour afficher le reçu complet.", styles["RecuCentre"]),
            Spacer(1, 2 * mm),
            Paragraph(f"Code : {_texte(code)}", styles["RecuCode"]),
            Spacer(1, 1 * mm),
            Paragraph(f"Généré le {_texte(date_generation)}", styles["RecuCentre"]),
        ],
    ]], colWidths=[43 * mm, 129 * mm])
    panneau_qr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COULEUR_DOUCE)),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(COULEUR_LIGNE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))

    elements = [
        marque,
        Spacer(1, 14 * mm),
        Paragraph(_texte(titre), styles["RecuTitre"]),
        Paragraph(_texte(sous_titre), styles["RecuSousTitre"]),
        Spacer(1, 10 * mm),
        table_details,
        Spacer(1, 7 * mm),
        total,
        Spacer(1, 12 * mm),
        panneau_qr,
    ]

    def pied_de_page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(COULEUR_LIGNE))
        canvas.line(18 * mm, 15 * mm, largeur_page - 18 * mm, 15 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#71817C"))
        canvas.drawString(18 * mm, 10 * mm, f"{NOM_APPLICATION} · Copie certifiée")
        canvas.drawRightString(largeur_page - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(elements, onFirstPage=pied_de_page, onLaterPages=pied_de_page)
    return tampon.getvalue()
