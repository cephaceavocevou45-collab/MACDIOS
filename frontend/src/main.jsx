import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { branding } from "./config/branding";
import { initialiserSentry } from "./sentry";
import "./index.css";

document.title = `${branding.appName} — Gestion de commerce`;
initialiserSentry();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode><App /></React.StrictMode>,
);
