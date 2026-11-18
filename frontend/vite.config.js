import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

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

export default defineConfig({ plugins: [react(), versionDeploiement] });
