"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, ArrowUpRight, BookOpen, Database, ExternalLink, Search, ShieldCheck } from "lucide-react";

type Study = {
  title: string;
  publication_year: number | null;
  doi: string | null;
  authors: string[];
  abstract: string | null;
  identity_status: "verified" | "probable" | "unresolved";
  locations: { provider: string; url: string; provider_record_id: string | null }[];
};

type DuplicateCandidate = {
  left: { provider: string; title: string; url: string };
  right: { provider: string; title: string; url: string };
  confidence: number;
  resolution: string;
};

type ResearchResult = {
  status: string;
  query: string;
  message?: string;
  studies: Study[];
  duplicate_candidates: DuplicateCandidate[];
  sources_searched: string[];
  source_failures?: { source: string; error: string }[];
  raw_records_found?: number;
  unique_studies?: number;
};

const API_URL = process.env.NEXT_PUBLIC_OPAL_API_URL ?? "http://127.0.0.1:8000";

export default function ResearchPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runResearch(nextQuestion: string) {
    const cleanQuestion = nextQuestion.trim();
    if (!cleanQuestion) return;
    setQuestion(cleanQuestion);
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: cleanQuestion }),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Engine returned ${response.status}`);
      }
      const data = (await response.json()) as ResearchResult;
      setResult(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const requestedQuestion = new URLSearchParams(window.location.search).get("q");
    if (requestedQuestion) void runResearch(requestedQuestion);
    // Read the initial URL once when the workspace opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runResearch(question);
  }

  return (
    <main className="live-workspace">
      <header className="live-header">
        <a className="brand" href="/">
          <span className="brand-mark"><span /></span>
          <span>opal<span className="brand-period">.</span></span>
        </a>
        <div className="live-header-right">
          <span><span className="engine-status-dot" /> Research engine</span>
          <a href="/">New question <ArrowUpRight size={14} /></a>
        </div>
      </header>

      <section className="live-content">
        <a className="back-link" href="/"><ArrowLeft size={14} /> Back to OPAL</a>
        <div className="live-kicker">RESEARCH WORKSPACE</div>
        <h1>Explore the evidence.</h1>
        <p className="live-intro">Search scholarly sources, inspect the original records and see where the same study appears across different websites.</p>

        <form className="live-search-form" onSubmit={handleSubmit}>
          <Search size={18} />
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Enter a research question or topic..."
            aria-label="Research question"
          />
          <button type="submit" disabled={loading || question.trim().length < 5}>
            {loading ? "Searching..." : "Search sources"}
          </button>
        </form>

        <div className="engine-note"><ShieldCheck size={14} /> OPAL keeps study records separate from the websites that host them. A mirror is not counted as a second study.</div>

        {loading && (
          <div className="live-state">
            <div className="loading-line" />
            <strong>Searching connected sources</strong>
            <p>Retrieving publication metadata and checking study identifiers.</p>
          </div>
        )}

        {error && (
          <div className="live-error" role="alert">
            <strong>Could not reach the research engine.</strong>
            <p>{error}</p>
            <span>Start the Python API in a second terminal, then search again.</span>
          </div>
        )}

        {result && !loading && (
          <section className="live-results">
            <div className="results-heading">
              <div>
                <div className="live-kicker">SEARCH RESULTS</div>
                <h2>{result.unique_studies ?? result.studies.length} study records</h2>
                <p>{result.raw_records_found ?? result.studies.length} source records retrieved for “{result.query}”.</p>
              </div>
              <div className="source-count"><Database size={15} /> {result.sources_searched.length} source connector{result.sources_searched.length === 1 ? "" : "s"}</div>
            </div>

            {result.message && <div className="live-empty">{result.message}</div>}

            {result.studies.length > 0 && (
              <div className="study-list">
                {result.studies.map((study, index) => (
                  <article className="study-row" key={study.doi ?? `${study.title}-${index}`}>
                    <div className="study-number">{String(index + 1).padStart(2, "0")}</div>
                    <div className="study-main">
                      <h3>{study.title}</h3>
                      <p className="study-meta">
                        {study.authors.slice(0, 4).join(", ")}
                        {study.authors.length > 4 ? " et al." : ""}
                        {study.publication_year ? ` · ${study.publication_year}` : ""}
                      </p>
                      {study.abstract && <p className="study-abstract">{study.abstract.replace(/<[^>]*>/g, "").slice(0, 420)}{study.abstract.length > 420 ? "…" : ""}</p>}
                      {study.doi && <span className="study-doi">DOI: {study.doi}</span>}
                      <div className="study-locations">
                        {study.locations.map((location) => (
                          <a href={location.url} key={location.url} target="_blank" rel="noreferrer">
                            {location.provider} <ExternalLink size={12} />
                          </a>
                        ))}
                        <span className={study.identity_status === "verified" ? "identity-verified" : "identity-unresolved"}>
                          {study.identity_status === "verified" ? "Identifier verified" : "Identity not yet verified"}
                        </span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}

            {result.duplicate_candidates.length > 0 && (
              <section className="duplicate-review">
                <div className="live-kicker">POSSIBLE DUPLICATES</div>
                <h3>Records that may describe the same study</h3>
                <p>These are flagged for review, not automatically merged. Similar titles alone are not enough to prove two records are identical.</p>
                {result.duplicate_candidates.map((candidate, index) => (
                  <div className="duplicate-pair" key={index}>
                    <span>{candidate.left.provider}: {candidate.left.title}</span>
                    <span>{candidate.right.provider}: {candidate.right.title}</span>
                    <strong>{Math.round(candidate.confidence * 100)}% similarity</strong>
                  </div>
                ))}
              </section>
            )}

            {result.source_failures && result.source_failures.length > 0 && (
              <div className="source-failures">
                {result.source_failures.map((failure) => <p key={failure.source}>{failure.source}: {failure.error}</p>)}
              </div>
            )}
          </section>
        )}

        {!result && !loading && !error && (
          <div className="workspace-start">
            <BookOpen size={20} />
            <h2>Start with a topic.</h2>
            <p>Try a research question above. OPAL currently searches scholarly publication metadata; survey databases and discussion platforms will be added as separate connectors.</p>
          </div>
        )}

        <footer className="live-footer">OPAL · Early research engine · Search results are publication metadata, not yet validated opinion findings.</footer>
      </section>
    </main>
  );
}
