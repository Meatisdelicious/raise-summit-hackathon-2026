import { Link } from "react-router-dom";
import { Reveal } from "./Reveal";
import "./landing.css";

/* --- Small hand-rolled line icons (no icon dependency, keeps the warm/human register) --- */
function IconHouse() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 11 12 4l8 7" />
      <path d="M6 10v9h12v-9" />
      <path d="M12 19v-4a2 2 0 0 1 2-2" />
    </svg>
  );
}
function IconLeaf() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 19c0-8 6-13 14-13 0 8-5 14-13 14" />
      <path d="M5 19c3-4 6-6 9-7" />
    </svg>
  );
}
function IconPeople() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <path d="M16 5.5a3 3 0 0 1 0 5.8" />
      <path d="M18 14.2c2 .9 3.5 2.9 3.5 5.3" />
    </svg>
  );
}
function IconFolder() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
    </svg>
  );
}
function IconBook() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 5a2 2 0 0 1 2-2h5v16H6a2 2 0 0 0-2 2Z" />
      <path d="M20 5a2 2 0 0 0-2-2h-5v16h5a2 2 0 0 1 2 2Z" />
    </svg>
  );
}
function IconChart() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 19h16" />
      <path d="M5 15l4-5 3 3 5-7" />
    </svg>
  );
}
function IconSpark() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
      <path d="M8 8l2 2M14 14l2 2M16 8l-2 2M10 14l-2 2" />
    </svg>
  );
}
function IconInstagram() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17" cy="7" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
function IconLinkedIn() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
      <path d="M4.98 3.5A2.5 2.5 0 1 0 5 8.5a2.5 2.5 0 0 0 0-5ZM3 9h4v12H3Zm7 0h3.8v1.7h.05c.53-.95 1.83-1.95 3.77-1.95 4.03 0 4.78 2.5 4.78 5.75V21h-4v-5.3c0-1.26-.02-2.9-1.77-2.9s-2.04 1.38-2.04 2.8V21H10Z" />
    </svg>
  );
}

const features = [
  {
    tint: "rose",
    icon: <IconHouse />,
    title: "Ancré dans le protocole",
    body: "Chaque conclusion renvoie à un article de SOP numéroté, consultable en un clic.",
  },
  {
    tint: "plum",
    icon: <IconLeaf />,
    title: "Le calcul décide, pas le modèle",
    body: "Des calculateurs déterministes fixent le signal d'escalade. Le modèle ne rend jamais de verdict autonome.",
  },
  {
    tint: "sage",
    icon: <IconPeople />,
    title: "Le clinicien tranche",
    body: "MILA prépare une escalade citée ; le biologiste valide avant toute action.",
  },
];

const steps = [
  {
    n: "1",
    tint: "coral",
    icon: <IconFolder />,
    title: "Reconstruire",
    body: "La trajectoire hormonale complète, jamais la valeur du jour isolée.",
  },
  {
    n: "2",
    tint: "plum",
    icon: <IconBook />,
    title: "Calculer",
    body: "Vitesse d'E2, composite OHSS, progestérone selon le jour du cycle.",
  },
  {
    n: "3",
    tint: "sage",
    icon: <IconChart />,
    title: "Escalader",
    body: "La règle de protocole qui s'applique, citée, prête à valider.",
  },
];

export function LandingPage() {
  return (
    <div className="selene-landing">
      <header className="ls-nav">
        <a className="ls-nav__brand" href="#top">
          MILA
        </a>
        <nav className="ls-nav__links" aria-label="Navigation principale">
          <a href="#features">Le produit</a>
          <a href="#how">Comment ça marche</a>
          <a href="#safety">Sécurité</a>
          <Link to="/app">Connexion</Link>
        </nav>
        <Link to="/app" className="ls-btn ls-btn--primary ls-nav__cta">
          <IconSpark />
          Voir la démo
        </Link>
      </header>

      <main id="top">
        {/* --- Hero --- */}
        <section className="ls-hero">
          <span className="ls-blob ls-blob--1" aria-hidden="true" />
          <Reveal className="ls-hero__copy">
            <h1 className="ls-hero__title">
              Une lecture plus sûre de chaque{" "}
              <span className="ls-accent-text">cycle de stimulation</span>
            </h1>
            <p className="ls-hero__lede">
              MILA assiste le biologiste et le clinicien&nbsp;: à chaque nouveau dosage hormonal, il
              reconstruit la trajectoire, calcule les signaux de risque et prépare une escalade
              citée, prête à valider en lien avec l'équipe médicale.
            </p>
            <div className="ls-hero__actions">
              <Link to="/app" className="ls-btn ls-btn--primary ls-btn--lg">
                Voir une revue en direct →
              </Link>
              <a href="#how" className="ls-btn ls-btn--ghost ls-btn--lg">
                Découvrir la méthode
              </a>
            </div>
            <p className="ls-hero__chips">
              <span>Cité</span>
              <span aria-hidden="true">·</span>
              <span>Validé par un humain</span>
              <span aria-hidden="true">·</span>
              <span>Souverain (EU / HDS)</span>
            </p>
          </Reveal>

          <Reveal className="ls-hero__media">
            <img
              className="ls-hero__photo"
              src="/frontpage.png"
              alt="Une biologiste échangeant avec une patiente"
              width="461"
              height="405"
            />
          </Reveal>
        </section>

        {/* --- Feature trio --- */}
        <section id="features" className="ls-features">
          <Reveal stagger>
            <div className="ls-feature-grid">
              {features.map((f) => (
                <article key={f.title} className="ls-feature">
                  <span className={`ls-feature__ic ls-feature__ic--${f.tint}`}>{f.icon}</span>
                  <h3 className="ls-feature__title">{f.title}</h3>
                  <p className="ls-feature__body">{f.body}</p>
                </article>
              ))}
            </div>
          </Reveal>
        </section>

        {/* --- How it works --- */}
        <section id="how" className="ls-how">
          <Reveal>
            <h2 className="ls-h2 ls-center">Comment MILA raisonne</h2>
            <p className="ls-how__sub ls-center">
              Un fil de raisonnement, pas une simple recherche.
            </p>
          </Reveal>
          <Reveal stagger>
            <div className="ls-steps">
              {steps.map((s) => (
                <article key={s.n} className="ls-step">
                  <span className={`ls-step__num ls-step__num--${s.tint}`}>{s.n}</span>
                  <span className="ls-step__ic">{s.icon}</span>
                  <h3 className="ls-step__title">{s.title}</h3>
                  <p className="ls-step__body">{s.body}</p>
                </article>
              ))}
            </div>
          </Reveal>
        </section>

        {/* --- Testimonial --- */}
        <section className="ls-quote-wrap">
          <Reveal className="ls-quote">
            <span className="ls-quote__mark" aria-hidden="true">
              &ldquo;
            </span>
            <blockquote>
              Avec MILA, la bonne règle arrive citée au bon moment. Je valide et je n'ai plus à
              reconstruire chaque trajectoire à la main.
            </blockquote>
            <div className="ls-quote__by">
              <span className="ls-quote__avatar" aria-hidden="true" />
              <div>
                <strong>Biologiste médical</strong>
                <span>Témoignage fictif</span>
              </div>
            </div>
          </Reveal>
        </section>

        {/* --- Safety strip --- */}
        <section id="safety" className="ls-safety-band">
          <Reveal className="ls-safety-band__inner">
            <p className="ls-eyebrow">Sécurité &amp; souveraineté</p>
            <h2 className="ls-h2">Une aide à la décision, le clinicien dans la boucle.</h2>
            <p className="ls-safety-band__lede">
              Données de santé sérielles = données sensibles (Article&nbsp;9). L'inférence et le
              corpus de protocoles restent dans une région EU, alignée HDS. Rien n'est envoyé sans
              validation humaine, et jamais à la patiente.
            </p>
          </Reveal>
        </section>

        {/* --- CTA --- */}
        <section className="ls-cta">
          <span className="ls-blob ls-blob--2" aria-hidden="true" />
          <span className="ls-blob ls-blob--3" aria-hidden="true" />
          <Reveal className="ls-cta__inner">
            <div>
              <h2 className="ls-cta__title">Voir MILA fermer la boucle sur un cycle</h2>
              <p className="ls-cta__lede">
                Une approche plus lisible et plus sûre du monitoring de stimulation, présentée sur un cas de
                démonstration entièrement synthétique.
              </p>
            </div>
            <Link to="/app" className="ls-btn ls-btn--primary ls-btn--lg">
              Ouvrir une revue →
            </Link>
          </Reveal>
        </section>
      </main>

      <footer className="ls-footer">
        <span className="ls-footer__brand">MILA</span>
        <nav className="ls-footer__links" aria-label="Liens de pied de page">
          <a href="#safety">Confidentialité</a>
          <a href="#top">Contact</a>
          <a href="#safety">Mentions légales</a>
        </nav>
        <div className="ls-footer__social">
          <a href="#top" aria-label="Instagram">
            <IconInstagram />
          </a>
          <a href="#top" aria-label="LinkedIn">
            <IconLinkedIn />
          </a>
        </div>
      </footer>
    </div>
  );
}
