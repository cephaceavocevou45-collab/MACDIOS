function normaliser(texte) {
  return texte.toLocaleLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[’`]/g, "'")
    .replace(/[٠-٩]/g, (chiffre) => String("٠١٢٣٤٥٦٧٨٩".indexOf(chiffre)))
    .replace(/[۰-۹]/g, (chiffre) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(chiffre)));
}

export function lireNombreDicte(texte) {
  const chiffre = normaliser(texte).match(/\d[\d\s.,]*/);
  if (chiffre) {
    let valeur = chiffre[0].replace(/\s/g, "").replace(/[^\d.,]/g, "");
    const virgule = valeur.lastIndexOf(",");
    const point = valeur.lastIndexOf(".");
    const separateur = Math.max(virgule, point);
    if (separateur >= 0 && valeur.length - separateur - 1 === 3 && !(virgule >= 0 && point >= 0)) valeur = valeur.replace(/[.,]/g, "");
    else if (virgule >= 0 && point >= 0) {
      valeur = valeur.replace(separateur === virgule ? /\./g : /,/g, "").replace(separateur === virgule ? "," : ".", ".");
    } else valeur = valeur.replace(",", ".");
    const nombre = Number(valeur);
    if (Number.isFinite(nombre)) return String(nombre);
  }

  const mots = normaliser(texte).match(/[a-z]+/g) || [];
  const unites = { zero: 0, un: 1, une: 1, deux: 2, trois: 3, quatre: 4, cinq: 5, six: 6, sept: 7, huit: 8, neuf: 9, dix: 10, onze: 11, douze: 12, treize: 13, quatorze: 14, quinze: 15, seize: 16 };
  const dizaines = { vingt: 20, trente: 30, quarante: 40, cinquante: 50, soixante: 60, septante: 70, octante: 80, nonante: 90 };
  let total = 0;
  let courant = 0;
  let reconnu = false;
  for (let index = 0; index < mots.length; index += 1) {
    const mot = mots[index];
    if (["et", "a", "cfa", "fcfa", "franc", "francs"].includes(mot)) continue;
    if (mot === "quatre" && ["vingt", "vingts"].includes(mots[index + 1])) {
      courant += 80; reconnu = true; index += 1;
      if (unites[mots[index + 1]] !== undefined) courant += unites[mots[++index]];
    } else if (dizaines[mot]) { courant += dizaines[mot]; reconnu = true; }
    else if (unites[mot] !== undefined) { courant += unites[mot]; reconnu = true; }
    else if (mot === "cent" || mot === "cents") { courant = (courant || 1) * 100; reconnu = true; }
    else if (mot === "mille") { total += (courant || 1) * 1000; courant = 0; reconnu = true; }
  }
  return reconnu ? String(total + courant) : "";
}

function indexOriginal(texte, offsetNormalise) {
  let normalise = 0;
  let original = 0;
  for (const caractere of texte) {
    if (normalise >= offsetNormalise) break;
    normalise += normaliser(caractere).length;
    original += caractere.length;
  }
  return original;
}

function nettoyerSegment(texte) {
  return texte.replace(/^\s*(?:est|égal à|egale a|de|du|:|-)\s*/i, "").replace(/[\s,;:.]+$/, "").trim();
}

/** Mappe une phrase dite sur les champs et libellés fournis par le formulaire. */
export function extraireChampsDictee(texte, definitions, champNom = "nom") {
  const normalise = normaliser(texte);
  const reperes = [];
  for (const [cle, definition] of Object.entries(definitions)) {
    for (const libelle of definition.aliases) {
      const expression = new RegExp(`(^|[^\\p{L}\\p{N}])(${normaliser(libelle).replace(/ /g, "\\s+")})(?=$|[^\\p{L}\\p{N}])`, "giu");
      for (const correspondance of normalise.matchAll(expression)) {
        const debut = correspondance.index + correspondance[1].length;
        reperes.push({ cle, debut, fin: debut + correspondance[2].length, type: definition.type || "text" });
      }
    }
  }
  reperes.sort((a, b) => a.debut - b.debut || b.fin - a.fin);
  const uniques = reperes.filter((repere, index) => !reperes.slice(0, index).some((precedent) => precedent.cle === repere.cle && repere.debut < precedent.fin));
  const resultat = {};
  if (uniques.length && champNom) {
    const premierRepere = uniques[0];
    const avant = texte.slice(0, indexOriginal(texte, premierRepere.debut))
      .replace(/^\s*(?:ajoute|ajouter|crée|creer|nouveau|nouvelle|client|fournisseur|produit|vente|vends|vendre)?\s*(?:un|une)?\s*/i, "")
      .replace(/[\s,;:.]+$/, "").trim();
    // Dans « fournisseur Awa » ou « produit Riz local », le nom suit le libellé.
    const apres = premierRepere.cle === champNom
      ? nettoyerSegment(texte.slice(indexOriginal(texte, premierRepere.fin), indexOriginal(texte, uniques[1]?.debut ?? normalise.length)))
        .replace(/^(?:fournisseur|supplier|client|customer|produit|product|article|nom)\s+/i, "").trim()
      : "";
    const nom = avant || apres;
    if (nom) resultat[champNom] = nom;
  } else if (!uniques.length && champNom) {
    const nom = texte.replace(/^\s*(?:ajoute|ajouter|crée|creer|nouveau|nouvelle|client|fournisseur|produit|vente|vends|vendre)?\s*(?:un|une)?\s*/i, "").trim();
    if (nom) resultat[champNom] = nom;
  }
  uniques.forEach((repere, index) => {
    const debut = indexOriginal(texte, repere.fin);
    const fin = indexOriginal(texte, uniques[index + 1]?.debut ?? normalise.length);
    const segment = nettoyerSegment(texte.slice(debut, fin));
    if (!segment) return;
    if (repere.cle === champNom && resultat[champNom]) return;
    if (repere.type === "number") {
      const valeur = lireNombreDicte(segment);
      if (valeur !== "") resultat[repere.cle] = valeur;
    } else if (repere.type === "phone") {
      const valeur = segment.match(/\+?\d[\d\s().-]*/)?.[0]?.trim();
      if (valeur) resultat[repere.cle] = valeur;
    } else if (repere.type === "email") {
      const valeur = segment.match(/[^\s,;]+@[^\s,;]+/)?.[0];
      if (valeur) resultat[repere.cle] = valeur;
    } else if (repere.type === "digits") {
      const valeur = normaliser(segment).match(/[\d\s]+/)?.[0].replace(/\D/g, "");
      if (valeur) resultat[repere.cle] = valeur;
    } else {
      resultat[repere.cle] = segment;
    }
  });
  return resultat;
}
