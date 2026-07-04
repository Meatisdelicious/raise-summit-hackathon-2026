import { Link } from "react-router-dom";
import { Reveal } from "./Reveal";
import "./landing.css";

function Crescent({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" className={className} aria-hidden="true">
      <path
        d="M15.5 2.2a9.8 9.8 0 1 0 6.3 12.1A7.8 7.8 0 0 1 15.5 2.2Z"
        fill="currentColor"
      />
    </svg>
  );
}

function HeroVisual() {
  return (
    <div className="ls-window" aria-hidden="true">
      <div className="ls-window__bar">
        <span className="ls-window__dot" />
        <span className="ls-window__dot" />
        <span className="ls-window__dot" />
        <span className="ls-window__url">selene.app / app</span>
      </div>
      <div className="ls-hero__visual">
      <svg viewBox="0 0 480 340" className="ls-hero__svg" role="img">
        <defs>
          <linearGradient id="ls-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8e5b7a" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#8e5b7a" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* soft grid */}
        <g stroke="#e6dcd4" strokeWidth="1">
          <line x1="48" y1="60" x2="440" y2="60" />
          <line x1="48" y1="130" x2="440" y2="130" />
          <line x1="48" y1="200" x2="440" y2="200" />
          <line x1="48" y1="270" x2="440" y2="270" />
        </g>

        {/* crescent, upper-left */}
        <g transform="translate(70 66)">
          <path
            d="M18 -14a20 20 0 1 0 13 26A16 16 0 0 1 18 -14Z"
            fill="#c9a24b"
            opacity="0.85"
          />
        </g>

        {/* estradiol area + curve */}
        <path
          d="M48 270 C 150 258, 210 232, 268 196 S 372 96, 440 66 L 440 270 Z"
          fill="url(#ls-area)"
        />
        <path
          d="M48 270 C 150 258, 210 232, 268 196 S 372 96, 440 66"
          fill="none"
          stroke="#8e5b7a"
          strokeWidth="3"
          strokeLinecap="round"
        />

        {/* progesterone, quiet secondary line */}
        <path
          d="M48 286 C 170 284, 300 280, 440 250"
          fill="none"
          stroke="#b89b72"
          strokeWidth="2"
          strokeDasharray="2 6"
          strokeLinecap="round"
        />

        {/* flagged inflection point */}
        <circle cx="372" cy="112" r="6.5" fill="#fbf8f4" stroke="#8e5b7a" strokeWidth="3" />
        <line x1="372" y1="112" x2="372" y2="60" stroke="#8e5b7a" strokeWidth="1" strokeDasharray="3 3" />
      </svg>

      <div className="ls-hero__chip">
        <span className="ls-hero__chip-dot" />
        <div>
          <strong>OHSS risk · escalated</strong>
          <span>SOP §4.2 · cited · awaiting validation</span>
        </div>
      </div>
      </div>
    </div>
  );
}

const risks = [
  {
    title: "Ovarian hyperstimulation",
    body: "A steep estradiol trajectory in a high responder can tip into OHSS. Caught on the curve — not the single value — management still has room: coasting, trigger modification, freeze-all.",
  },
  {
    title: "Premature luteinization",
    body: "A progesterone rise at the wrong cycle day quietly lowers fresh-transfer odds. The decision it forces is time-sensitive, and easy to miss on a busy panel.",
  },
  {
    title: "Poor response",
    body: "A flat curve against the expected stimulation response, recognised too late, means a wasted cycle for a patient who may have few attempts left.",
  },
];

const steps = [
  {
    n: "01",
    title: "Rebuild the trajectory",
    body: "Prior serial results, protocol type, cycle day, and baseline reserve (AMH, antral follicle count, PCOS) — the whole cycle, not today's number in isolation.",
  },
  {
    n: "02",
    title: "Compute the signals",
    body: "E2 rate-of-rise, estradiol per mature follicle, the OHSS composite, progesterone-for-cycle-day. Deterministic calculators — never a language model's guess.",
  },
  {
    n: "03",
    title: "Retrieve only what the math calls for",
    body: "Which protocol article to pull is decided by what just computed. The OHSS SOP is never touched for a routine patient. This is why Selene is an agent, not a search.",
    accent: true,
  },
  {
    n: "04",
    title: "A cited brief, escalated to validate",
    body: "Every clause resolves to a numbered protocol article. A biologist approves, edits, or rejects before anything reaches the clinic. Selene drafts; the human decides.",
  },
];

const states = [
  "Routine — continue",
  "OHSS risk",
  "Premature luteinization",
  "Poor response",
  "Missing timepoint",
  "Needs review",
];

const safety = [
  {
    title: "Deterministic where it matters",
    body: "Calculators and protocol rules decide the escalation flag. The model interprets and writes prose — it never issues an autonomous clinical verdict.",
  },
  {
    title: "Everything is cited",
    body: "Each recommendation resolves to a numbered protocol / SOP article. No ungrounded advice ships, and every brief is auditable line by line.",
  },
  {
    title: "Human validation, always",
    body: "The output is professional decision support for the biologist and clinician — never patient-facing. No brief is auto-sent.",
  },
  {
    title: "Sovereign by design",
    body: "Serial hormone data is Article-9 sensitive. Inference and the protocol corpus stay in an EU region, HDS-aligned — the sovereign alternative to data leaving the EU.",
  },
];

export function LandingPage() {
  return (
    <div className="selene-landing">
      <header className="ls-nav">
        <a className="ls-nav__brand" href="#top">
          <Crescent className="ls-nav__mark" />
          Selene
        </a>
        <nav className="ls-nav__links" aria-label="Primary">
          <a href="#problem">The problem</a>
          <a href="#how">How it works</a>
          <a href="#safety">Safety</a>
        </nav>
        <Link to="/app" className="ls-btn ls-btn--primary ls-nav__cta">
          See it live
        </Link>
      </header>

      <main id="top">
        <section className="ls-hero">
          <Reveal className="ls-hero__copy">
            <p className="ls-eyebrow">Clinical monitoring intelligence · IVF laboratories</p>
            <h1 className="ls-hero__title">
              Every hormone value, read in the light of the whole cycle.
            </h1>
            <p className="ls-hero__lede">
              Selene sits between the assay and the clinician. For each new monitoring result in an
              ovarian-stimulation cycle, it rebuilds the trajectory, computes the risk signals, and
              surfaces the exact protocol rule that applies — as a cited, ready-to-validate
              escalation brief.
            </p>
            <div className="ls-hero__actions">
              <Link to="/app" className="ls-btn ls-btn--primary">
                See a live review
              </Link>
              <a href="#how" className="ls-btn ls-btn--ghost">
                How it reasons
              </a>
            </div>
            <p className="ls-hero__note">
              For lab biologists &amp; PMA clinicians · never patient-facing
            </p>
          </Reveal>
          <Reveal>
            <HeroVisual />
          </Reveal>
        </section>

        <div className="ls-trustbar">
          <span>Grounded in protocol</span>
          <span>Human-validated</span>
          <span>EU / HDS-aligned</span>
          <span>Synthetic data only</span>
        </div>

        <section id="problem" className="ls-section">
          <Reveal className="ls-section__head">
            <p className="ls-eyebrow">The problem</p>
            <h2 className="ls-h2">A mis-timed value doesn&rsquo;t announce itself.</h2>
            <p className="ls-section__lede">
              In serial hormonal monitoring, one late, missing, or mis-read draw cascades. The lab
              delivers numbers; the intelligence to escalate the right one, in time, is left to a
              human scanning a busy panel.
            </p>
          </Reveal>
          <Reveal stagger>
            <div className="ls-cards">
              {risks.map((risk) => (
                <article key={risk.title} className="ls-card">
                  <span className="ls-card__rule" />
                  <h3 className="ls-card__title">{risk.title}</h3>
                  <p className="ls-card__body">{risk.body}</p>
                </article>
              ))}
            </div>
          </Reveal>
        </section>

        <section id="how" className="ls-section ls-section--dark">
          <Reveal className="ls-section__head">
            <p className="ls-eyebrow">How it works</p>
            <h2 className="ls-h2">Not a lookup. A line of reasoning.</h2>
            <p className="ls-section__lede">
              The conditional retrievals can&rsquo;t be issued up front — which rule Selene needs is
              unknown until the computation reveals the concern, and that computation is impossible
              until the trajectory is rebuilt. The dependency graph forbids retrieve-then-answer.
            </p>
          </Reveal>
          <Reveal stagger>
            <ol className="ls-steps">
              {steps.map((step) => (
                <li key={step.n} className={`ls-step${step.accent ? " ls-step--accent" : ""}`}>
                  <span className="ls-step__n">{step.n}</span>
                  <div>
                    <h3 className="ls-step__title">{step.title}</h3>
                    <p className="ls-step__body">{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Reveal>
          <Reveal className="ls-states">
            <p className="ls-states__label">Every run resolves to one constrained outcome</p>
            <div className="ls-states__chips">
              {states.map((state) => (
                <span key={state} className="ls-chip">
                  {state}
                </span>
              ))}
            </div>
          </Reveal>
        </section>

        <section id="safety" className="ls-section">
          <Reveal className="ls-section__head">
            <p className="ls-eyebrow">Safety &amp; sovereignty</p>
            <h2 className="ls-h2">Decision support, with the clinician in the loop.</h2>
          </Reveal>
          <Reveal stagger>
            <div className="ls-safety">
              {safety.map((item) => (
                <article key={item.title} className="ls-safety__item">
                  <h3 className="ls-safety__title">{item.title}</h3>
                  <p className="ls-safety__body">{item.body}</p>
                </article>
              ))}
            </div>
          </Reveal>
        </section>

        <section className="ls-cta">
          <Reveal>
            <Crescent className="ls-cta__mark" />
            <h2 className="ls-cta__title">See Selene close the loop on a live cycle.</h2>
            <p className="ls-cta__lede">
              Watch it rebuild a trajectory, compute the risk, fetch the governing rule, and draft
              the cited escalation — on a fully synthetic demo case.
            </p>
            <Link to="/app" className="ls-btn ls-btn--primary ls-btn--lg">
              Open the live review
            </Link>
          </Reveal>
        </section>
      </main>

      <footer className="ls-footer">
        <div className="ls-footer__brand">
          <Crescent className="ls-nav__mark" />
          Selene
        </div>
        <p className="ls-footer__disclaimer">
          Selene is a professional decision-support prototype built for the RAISE Summit Hackathon
          2026. Synthetic data only — not a medical device, and not a substitute for clinical
          judgement.
        </p>
      </footer>
    </div>
  );
}
