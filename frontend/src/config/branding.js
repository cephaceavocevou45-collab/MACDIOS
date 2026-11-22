// Modifiez cette configuration pour adapter le nom, les coordonnées et les liens publics.
const whatsappContact = "https://wa.me/2290157179683";

export const branding = {
  appName: "MACDIOS",
  appShortName: "MACD",
  // Ancien nom de l'application, encore présent comme valeur initiale sur certains profils.
  legacyBrandNames: ["nobi"],
  appDescription: "La gestion simple de votre commerce, depuis votre téléphone.",
  logoMark: "M",
  // Palette utilisée uniquement par la page publique.
  palette: {
    primary: "#006747",
    primaryDark: "#004d38",
    accent: "#e9a900",
    background: "#f7f9f6",
    ink: "#17332a",
    muted: "#66786f",
    soft: "#e9f5ef",
    line: "#dce8de",
  },
  contact: {
    email: "cephacemacevo@gmail.com",
    telephone: "+2290157179683",
    whatsapp: whatsappContact,
    address: "Cotonou, Bénin",
    facebook: "",
  },
  // Laissez vide tant que l'adresse officielle du réseau n'est pas connue.
  socials: {
    facebook: "",
    instagram: "",
    whatsapp: whatsappContact,
    linkedin: "",
    tiktok: "",
    youtube: "",
  },
};

export function nomBoutiqueAffiche(nom) {
  const valeur = String(nom || "").trim();
  return branding.legacyBrandNames.includes(valeur.toLocaleLowerCase("fr"))
    ? branding.appName
    : valeur;
}
