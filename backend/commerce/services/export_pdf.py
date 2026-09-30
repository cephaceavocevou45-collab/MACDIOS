"""Construction d'un export PDF lisible, paginé et limité au commerçant demandeur."""

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from commerce.branding import COULEUR_APPLICATION, LOGO_APPLICATION, NOM_APPLICATION
from commerce.models import (
    Abonnement, Client, CorrectionDette, DemandePaiementManuel, Dette, Paiement,
    PaiementAbonnementHistorique, Produit, Vente,
)


def _texte(valeur):
    """Échappe le texte utilisateur avant de le passer au parseur XML de ReportLab."""
    return escape(str(valeur if valeur not in (None, "") else "—"))


def _date(valeur):
    if valeur is None:
        return "—"
    if timezone.is_aware(valeur):
        valeur = timezone.localtime(valeur)
    return valeur.strftime("%d/%m/%Y %H:%M")


def _fcfa(valeur):
    return f"{Decimal(valeur or 0):,.0f}".replace(",", " ") + " FCFA"


def construire_export_pdf(commercant):
    """Génère en mémoire un PDF contenant exclusivement les objets de ce commerçant."""
    produits = list(Produit.objects.filter(commercant=commercant).order_by("nom"))
    clients = list(Client.objects.filter(commercant=commercant).order_by("nom"))
    ventes = list(Vente.objects.filter(commercant=commercant).select_related("produit", "client"))
    dettes = list(Dette.objects.filter(commercant=commercant).select_related("client"))
    corrections = list(CorrectionDette.objects.filter(commercant=commercant).select_related("dette__client"))
    paiements = list(Paiement.objects.filter(commercant=commercant).select_related("client"))
    abonnements = list(Abonnement.objects.filter(commercant=commercant).select_related("plan"))
    transactions = list(PaiementAbonnementHistorique.objects.filter(commercant=commercant).select_related("plan"))
    demandes = list(DemandePaiementManuel.objects.filter(commercant=commercant).select_related("plan"))

    # Deux agrégations séparées évitent le produit cartésien dettes × paiements.
    total_dettes = dict(Dette.objects.filter(commercant=commercant).values("client_id").annotate(total=Coalesce(Sum("montant"), Decimal("0"))).values_list("client_id", "total"))
    total_paiements = dict(Paiement.objects.filter(commercant=commercant).values("client_id").annotate(total=Coalesce(Sum("montant"), Decimal("0"))).values_list("client_id", "total"))

    tampon = BytesIO()
    largeur_page, hauteur_page = A4
    document = SimpleDocTemplate(
        tampon, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm, pageCompression=0,
        title=f"Export de données — {commercant.nom_boutique}",
        author=NOM_APPLICATION,
    )
    styles = getSampleStyleSheet()
    couleur_marque = colors.HexColor(COULEUR_APPLICATION)
    styles["Title"].textColor = couleur_marque
    styles["Title"].fontSize = 21
    styles["Title"].leading = 26
    styles.add(ParagraphStyle(
        name="SectionExport", parent=styles["Heading2"], textColor=couleur_marque,
        fontSize=13, leading=17, spaceBefore=9 * mm, spaceAfter=3 * mm, keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="PetitExport", parent=styles["BodyText"], fontSize=7.5, leading=10,
    ))
    styles.add(ParagraphStyle(
        name="EnteteExport", parent=styles["PetitExport"], textColor=colors.white, fontName="Helvetica-Bold",
    ))

    def paragraphe(valeur, style="PetitExport"):
        return Paragraph(_texte(valeur), styles[style])

    def tableau(titre, entetes, lignes, largeurs):
        """LongTable répète les entêtes et coupe les lignes entre les pages."""
        story.append(Paragraph(_texte(titre), styles["SectionExport"]))
        donnees = [[Paragraph(_texte(cellule), styles["EnteteExport"]) for cellule in entetes]]
        donnees.extend([[paragraphe(cellule) for cellule in ligne] for ligne in lignes])
        if not lignes:
            donnees.append([paragraphe("Aucune donnée enregistrée.")] + [paragraphe("") for _ in entetes[1:]])
        table = LongTable(donnees, colWidths=largeurs, repeatRows=1, splitByRow=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), couleur_marque),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f5")]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)

    story = [
        Paragraph(f'<font color="{COULEUR_APPLICATION}"><b>{_texte(LOGO_APPLICATION)} &nbsp; {_texte(NOM_APPLICATION)}</b></font>', styles["Heading2"]),
        Spacer(1, 3 * mm),
        Paragraph("Export de mes données", styles["Title"]),
        Paragraph(f"Généré le {_date(timezone.now())}", styles["BodyText"]),
    ]

    story.append(Paragraph("Informations du commerçant", styles["SectionExport"]))
    infos = [
        ["Nom de la boutique", commercant.nom_boutique],
        ["Adresse email", commercant.email],
        ["Téléphone", commercant.telephone or "Non renseigné"],
        ["Compte créé le", _date(commercant.date_joined)],
        ["Consentement enregistré le", _date(commercant.consentement_le)],
    ]
    info_table = LongTable([[Paragraph("Information", styles["EnteteExport"]), Paragraph("Valeur", styles["EnteteExport"])]] + [[paragraphe(a), paragraphe(b)] for a, b in infos], colWidths=[55 * mm, 125 * mm], repeatRows=1)
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), couleur_marque),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f5")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)

    tableau("Produits", ["Nom", "Prix", "Stock", "Seuil d’alerte", "Créé le"], [
        [p.nom, _fcfa(p.prix), p.quantite_stock, p.seuil_alerte, _date(p.date_creation)] for p in produits
    ], [48 * mm, 32 * mm, 20 * mm, 32 * mm, 48 * mm])

    tableau("Clients et soldes", ["Nom", "Téléphone", "Total des dettes", "Total des paiements", "Solde"], [
        [c.nom, c.telephone or "—", _fcfa(total_dettes.get(c.pk, 0)), _fcfa(total_paiements.get(c.pk, 0)), _fcfa(total_dettes.get(c.pk, 0) - total_paiements.get(c.pk, 0))]
        for c in clients
    ], [40 * mm, 34 * mm, 37 * mm, 39 * mm, 30 * mm])

    tableau("Historique des ventes", ["Date", "Produit", "Client", "Qté", "Prix unitaire", "Total"], [
        [_date(v.date), v.produit.nom, v.client.nom if v.client else "Vente directe", v.quantite, _fcfa(v.prix_unitaire), _fcfa(v.total)]
        for v in ventes
    ], [31 * mm, 38 * mm, 34 * mm, 12 * mm, 32 * mm, 33 * mm])

    mouvements = []
    mouvements.extend((d.date, [d.date, "Dette", d.client.nom, d.note or "Dette enregistrée", _fcfa(d.montant)]) for d in dettes)
    mouvements.extend((c.date, [c.date, "Correction", c.dette.client.nom, c.raison, f"{_fcfa(c.montant_precedent)} → {_fcfa(c.nouveau_montant)}"]) for c in corrections)
    mouvements.extend((p.date, [p.date, "Paiement", p.client.nom, "Paiement reçu", _fcfa(p.montant)]) for p in paiements)
    mouvements.sort(key=lambda element: element[0], reverse=True)
    tableau("Historique des dettes et paiements", ["Date", "Type", "Client", "Note / raison", "Montant"], [
        [_date(date), *ligne[1:]]
        for date, ligne in mouvements
    ], [31 * mm, 25 * mm, 35 * mm, 68 * mm, 21 * mm])

    story.append(Paragraph("Historique de l’abonnement", styles["SectionExport"]))
    for abonnement in abonnements:
        story.append(Paragraph(
            f"Formule actuelle : {_texte(abonnement.plan.nom)} — {_texte(abonnement.get_statut_display())} — "
            f"du {_date(abonnement.date_debut)} au {_date(abonnement.date_fin)}",
            styles["BodyText"],
        ))
        story.append(Spacer(1, 2 * mm))
    mouvements_abonnement = [
        (t.date_creation, [_date(t.date_creation), "Paiement automatique", t.plan.nom, t.statut, _fcfa(t.montant)])
        for t in transactions
    ]
    mouvements_abonnement.extend([
        (d.date_demande, [_date(d.date_demande), "Paiement manuel", d.plan.nom, d.get_statut_display(), _fcfa(d.montant)])
        for d in demandes
    ])
    mouvements_abonnement.sort(key=lambda mouvement: mouvement[0], reverse=True)
    lignes_abonnement = [ligne for _, ligne in mouvements_abonnement]
    tableau("Transactions et demandes", ["Date", "Mode", "Formule", "Statut", "Montant"], lignes_abonnement,
            [34 * mm, 34 * mm, 39 * mm, 40 * mm, 33 * mm])

    def pied_de_page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dce5e1"))
        canvas.line(15 * mm, 13 * mm, largeur_page - 15 * mm, 13 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64736e"))
        canvas.drawString(15 * mm, 8 * mm, f"{NOM_APPLICATION} · Export confidentiel")
        canvas.drawRightString(largeur_page - 15 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=pied_de_page, onLaterPages=pied_de_page)
    return tampon.getvalue()
