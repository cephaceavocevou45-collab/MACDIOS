import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { branding } from "./src/config/branding.js";

const rendreManifeste = (contenu) => contenu
  .replaceAll("__APP_NAME__", branding.appName)
  .replaceAll("__APP_SHORT_NAME__", branding.appShortName);

const manifesteApplication = {
  name: "manifest-application",
  transformIndexHtml(html) {
    return html.replaceAll("__APP_NAME__", branding.appName);
  },
  configureServer(server) {
    server.middlewares.use((request, response, next) => {
      if (request.url?.split("?")[0] !== "/manifest.webmanifest") return next();
      const chemin = resolve(process.cwd(), "public", "manifest.webmanifest");
      response.setHeader("Content-Type", "application/manifest+json; charset=utf-8");
      response.end(rendreManifeste(readFileSync(chemin, "utf8")));
    });
  },
  closeBundle() {
    const chemin = resolve(process.cwd(), "dist", "manifest.webmanifest");
    writeFileSync(chemin, rendreManifeste(readFileSync(chemin, "utf8")), "utf8");
  },
};

// Ce manifeste permet à la CI de vérifier le SHA réellement servi par Railway.
const versionDeploiement = {
  name: "nobi-version-deploiement",
  apply: "build",
  closeBundle() {
    const dossierSortie = resolve(process.cwd(), "dist");
    mkdirSync(dossierSortie, { recursive: true });
    writeFileSync(
      resolve(dossierSortie, "version.json"),
      JSON.stringify({ commit: process.env.APP_RELEASE_SHA || "unknown" }),
      "utf8",
    );
  },
};

export default defineConfig({ plugins: [react(), versionDeploiement, manifesteApplication] });
