import { LANGUES_INTERFACE, useLangue, TexteLocalise } from "../contexte/LangueContext";

export default function Parametres() {
  const { langue, setLangue, densite, setDensite } = useLangue();
  return <section className="mx-auto max-w-3xl space-y-6">
    <header className="space-y-2">
      <span className="form-eyebrow">{<TexteLocalise phrase={"Espace personnel"} />}</span>
      <h1 className="text-3xl font-bold text-ink">{<TexteLocalise phrase={"Paramètres"} />}</h1>
      <p className="text-ink-muted">{<TexteLocalise phrase={"Choisissez votre langue et l’affichage qui vous convient. Ces préférences sont enregistrées sur cet appareil."} />}</p>
    </header>

    <article className="space-y-5 rounded-2xl border border-line bg-white p-5 shadow-card sm:p-8">
      <div>
        <h2 className="font-semibold text-ink">{<TexteLocalise phrase={"Langue de l’interface"} />}</h2>
        <p className="mt-1 text-sm text-ink-muted">{<TexteLocalise phrase={"Choisissez parmi les langues actuellement proposées."} />}</p>
      </div>
      <label className="grid max-w-md gap-2 font-medium text-ink">
        <span>{<TexteLocalise phrase={"Langue"} />}</span>
        <select className="w-full rounded-xl border border-line bg-white px-4 py-3 text-base text-ink focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20" value={langue} onChange={(event) => setLangue(event.target.value)}>
          {LANGUES_INTERFACE.map((item) => <option key={item.code} value={item.code}>{item.nomLocal} — {item.nom}</option>)}
        </select>
      </label>
      <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-700" role="status">{<TexteLocalise phrase={"Les cinq langues proposées s’appliquent aux écrans de l’espace commerçant, du site public et du back-office."} />}</p>
    </article>

    <article className="space-y-5 rounded-2xl border border-line bg-white p-5 shadow-card sm:p-8">
      <div>
        <h2 className="font-semibold text-ink">{<TexteLocalise phrase={"Densité de l’affichage"} />}</h2>
        <p className="mt-1 text-sm text-ink-muted">{<TexteLocalise phrase={"Ajustez l’espace entre les éléments selon votre écran."} />}</p>
      </div>
      <label className="grid max-w-md gap-2 font-medium text-ink">
        <span>{<TexteLocalise phrase={"Disposition"} />}</span>
        <select className="w-full rounded-xl border border-line bg-white px-4 py-3 text-base text-ink focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20" value={densite} onChange={(event) => setDensite(event.target.value)}>
          <option value="confortable">{<TexteLocalise phrase={"Confortable — boutons et espaces plus grands"} />}</option>
          <option value="compacte">{<TexteLocalise phrase={"Compacte — davantage de contenu à l’écran"} />}</option>
        </select>
      </label>
    </article>
  </section>;
}
