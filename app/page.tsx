"use client";

import { FormEvent, useState } from "react";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronDown,
  CircleHelp,
  Database,
  FileSpreadsheet,
  Layers3,
  LockKeyhole,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";

const examples = [
  "Do people support a four-day work week?",
  "What matters most when choosing a university?",
  "How do city residents feel about public transport?",
];

const sampleRows = [
  { label: "Strongly support", value: 42, color: "var(--green)" },
  { label: "Somewhat support", value: 26, color: "#8DB8A4" },
  { label: "Neither / unsure", value: 14, color: "#C8D2CC" },
  { label: "Oppose", value: 18, color: "#D8A49A" },
];

export default function Home() {
  const [question, setQuestion] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) return;
    setSubmitted(true);
  }

  function useExample(example: string) {
    setQuestion(example);
    setSubmitted(false);
    document.getElementById("research-question")?.focus();
  }

  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#" aria-label="OPAL home">
          <span className="brand-mark"><span /></span>
          <span>opal<span className="brand-period">.</span></span>
        </a>

        <nav className="main-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#methodology">Methodology</a>
        </nav>

        <div className="header-right">
          <span className="no-account"><LockKeyhole size={13} /> No account required</span>
          <a className="header-link" href="#how-it-works">
            Explore OPAL <ArrowUpRight size={15} />
          </a>
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> THE OPINION RESEARCH ENGINE</div>
          <h1>Make sense of<br />what people <em>think.</em></h1>
          <p className="hero-description">
            Ask a question. OPAL gathers evidence from surveys, research and public
            discussions, then turns it into structured data you can actually use.
          </p>

          <form className="question-card" onSubmit={handleSubmit}>
            <label htmlFor="research-question">WHAT WOULD YOU LIKE TO KNOW?</label>
            <textarea
              id="research-question"
              value={question}
              onChange={(event) => {
                setQuestion(event.target.value);
                setSubmitted(false);
              }}
              placeholder="e.g. Do people support a four-day work week?"
              rows={2}
            />
            <div className="question-footer">
              <span className="input-hint"><Sparkles size={14} /> Natural language research</span>
              <button className="submit-button" type="submit" disabled={!question.trim()}>
                Start research <ArrowRight size={16} />
              </button>
            </div>
          </form>

          {submitted && (
            <div className="request-notice" role="status">
              <div className="notice-icon"><Check size={16} /></div>
              <div>
                <strong>Your research question is ready.</strong>
                <span>The research engine is the next component we'll connect. No results have been generated yet.</span>
              </div>
            </div>
          )}

          <div className="examples">
            <span className="examples-label">TRY AN EXAMPLE</span>
            <div className="example-list">
              {examples.map((example) => (
                <button key={example} type="button" onClick={() => useExample(example)}>
                  {example} <ArrowUpRight size={13} />
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="preview-wrap">
          <div className="preview-topline">
            <span><span className="live-dot" /> A LOOK INSIDE OPAL</span>
            <span className="preview-tag">ILLUSTRATIVE PREVIEW</span>
          </div>
          <div className="results-window">
            <div className="window-header">
              <div className="window-title">
                <div className="file-icon"><FileSpreadsheet size={17} /></div>
                <div>
                  <strong>Public opinion overview</strong>
                  <span>Example research output · not live data</span>
                </div>
              </div>
              <button className="more-button" aria-label="More options" type="button"><span /><span /><span /></button>
            </div>

            <div className="result-meta">
              <span className="meta-chip">WORK &amp; ECONOMY</span>
              <span>Example question</span>
            </div>
            <h3>Should the working week be four days?</h3>
            <p className="sample-description">Illustrative distribution of responses</p>

            <div className="chart-area">
              <div className="chart-summary">
                <div><strong>68%</strong><span>Support</span></div>
                <div className="summary-divider" />
                <div><strong>18%</strong><span>Oppose</span></div>
                <div className="summary-divider" />
                <div><strong>14%</strong><span>Unsure</span></div>
              </div>
              <div className="bar-list">
                {sampleRows.map((row) => (
                  <div className="bar-row" key={row.label}>
                    <div className="bar-label"><span>{row.label}</span><strong>{row.value}%</strong></div>
                    <div className="bar-track"><div style={{ width: row.value + "%", background: row.color }} /></div>
                  </div>
                ))}
              </div>
            </div>

            <div className="table-heading">
              <span><Layers3 size={14} /> EVIDENCE BREAKDOWN</span>
              <span>4 example rows</span>
            </div>
            <div className="mini-table">
              <div className="table-row table-head"><span>RESPONSE</span><span>SHARE</span><span>TYPE</span></div>
              <div className="table-row"><span>Strongly support</span><strong>42%</strong><span className="type-survey">Survey</span></div>
              <div className="table-row"><span>Somewhat support</span><strong>26%</strong><span className="type-survey">Survey</span></div>
              <div className="table-row"><span>Neither / unsure</span><strong>14%</strong><span className="type-report">Report</span></div>
            </div>
            <div className="window-footer">
              <span><ShieldCheck size={14} /> Evidence types kept separate</span>
              <span>CSV / XLSX export <ArrowDownRight size={13} /></span>
            </div>
          </div>
          <div className="preview-caption">
            <div className="caption-icon"><BarChart3 size={17} /></div>
            <span><strong>From question to usable data.</strong> Charts, evidence and exportable tables in one place.</span>
          </div>
        </div>
      </section>

      <section className="trust-strip" id="methodology">
        <div className="trust-intro">BUILT FOR BETTER QUESTIONS</div>
        <div className="trust-item"><BarChart3 size={17} /><span>Evidence, not guesswork</span></div>
        <div className="trust-item"><Database size={17} /><span>Traceable sources</span></div>
        <div className="trust-item"><ShieldCheck size={17} /><span>Clear methodology</span></div>
        <div className="trust-item"><Upload size={17} /><span>Export when you're done</span></div>
      </section>

      <section className="how-section" id="how-it-works">
        <div className="section-kicker">A MORE USEFUL WAY TO RESEARCH</div>
        <div className="how-heading">
          <h2>Research without<br /><em>the busywork.</em></h2>
          <p>No accounts. No endless tabs. Just a clear path from a question to evidence you can inspect, compare and take with you.</p>
        </div>
        <div className="steps-grid">
          <article className="step-card">
            <span className="step-number">01</span>
            <div className="step-icon"><Search size={20} /></div>
            <h3>Ask a question</h3>
            <p>Describe what you want to understand in your own words. OPAL identifies the topic, population and evidence needed.</p>
          </article>
          <article className="step-card">
            <span className="step-number">02</span>
            <div className="step-icon"><Database size={20} /></div>
            <h3>Gather evidence</h3>
            <p>Relevant surveys, studies and public discussions are found, assessed and organised by evidence type.</p>
          </article>
          <article className="step-card">
            <span className="step-number">03</span>
            <div className="step-icon"><FileSpreadsheet size={20} /></div>
            <h3>Take your data</h3>
            <p>Explore structured results, inspect sources and export your spreadsheet. Then you're free to go.</p>
          </article>
        </div>
      </section>

      <footer className="site-footer">
        <a className="brand footer-brand" href="#">
          <span className="brand-mark"><span /></span>
          <span>opal<span className="brand-period">.</span></span>
        </a>
        <span>Opinion research, made clear.</span>
        <span className="footer-note">No account. No noise. Just evidence.</span>
      </footer>
    </main>
  );
}
