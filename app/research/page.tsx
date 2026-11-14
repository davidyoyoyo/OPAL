"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
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

type SurveyResult = {
  id: string;
  question_text: string;
  population: string | null;
  sample_size: number | null;
  base_n: number | null;
  fieldwork_start: string | null;
  fieldwork_end: string | null;
  source_title: string;
  source_url: string;
  responses: { label: string; count: number | null; percentage: number | null }[];
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
  candidate_records_screened?: number;
  relevant_source_records?: number;
  findings?: { id: string; title: string; summary?: string; evidence_text: string; source_title: string; source_url: string; publication_year: number | null; evidence_type: string; evidence_level: string; interpretation: string }[];
  survey_results?: SurveyResult[];
  abstracts_with_evidence?: number;
  evidence_synthesis?: {
    mode: "ai_synthesis" | "extractive_fallback";
    overview: string;
    key_points: {
      text: string;
      source_ids: string[];
      source_title?: string | null;
      source_url?: string | null;
      publication_year?: number | null;
    }[];
    limitations: string[];
  };
  survey_data_status?: { status: string; message: string };
};

const API_URL = process.env.NEXT_PUBLIC_OPAL_API_URL ?? "http://127.0.0.1:8000";

export default function ResearchPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [visibleStudies, setVisibleStudies] = useState(3);
  const [visibleMethodology, setVisibleMethodology] = useState(3);

  async function runResearch(nextQuestion: string) {
    const cleanQuestion = nextQuestion.trim();
    if (!cleanQuestion) return;
    setQuestion(cleanQuestion);
    setLoading(true);
    setError("");
    setResult(null);
    setVisibleStudies(3);
    setVisibleMethodology(3);

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
                <h2>{result.unique_studies ?? result.studies.length} relevant studies</h2>
                <p>{result.unique_studies ?? result.studies.length} relevant studies retained from {result.candidate_records_screened ?? result.raw_records_found ?? result.studies.length} records screened for “{result.query}”.</p>
              </div>
              <div className="source-count"><Database size={15} /> {result.sources_searched.length} source connector{result.sources_searched.length === 1 ? "" : "s"}</div>
            </div>

            <section className="survey-data-section">
              <div className="findings-heading">
                <div>
                  <div className="live-kicker">SURVEY MEASUREMENTS</div>
                  <h3>Measured opinions</h3>
                </div>
                <span className="findings-count">{result.survey_results?.length ?? 0} datasets</span>
              </div>
              {result.survey_results && result.survey_results.length > 0 ? (
                <div className="survey-results-list">
                  {result.survey_results.map((survey) => (
                    <article className="survey-result-card" key={survey.id}>
                      <h4>{survey.question_text}</h4>
                      <div className="survey-meta">
                        <span>Asked to: {survey.population ?? "Not specified"}</span>
                        <span>Question base: {survey.base_n?.toLocaleString() ?? "Not reported"}</span>
                        <span>Sample: {survey.sample_size?.toLocaleString() ?? "Not reported"}</span>
                        {survey.fieldwork_start && <span>Fieldwork: {survey.fieldwork_start}{survey.fieldwork_end ? ` – ${survey.fieldwork_end}` : ""}</span>}
                      </div>
                      <div className="survey-bars">
                        {survey.responses.map((response, index) => (
                          <div className="survey-bar-row" key={`${survey.id}-${index}`}>
                            <div><span>{response.label}</span><strong>{response.percentage === null ? "—" : `${response.percentage.toFixed(1)}%`}</strong></div>
                            <div className="survey-bar-track"><span style={{ width: `${Math.max(0, Math.min(100, response.percentage ?? 0))}%` }} /></div>
                            <small>{response.count === null ? "Count not reported" : `${response.count.toLocaleString()} responses`}</small>
                          </div>
                        ))}
                      </div>
                      <a href={survey.source_url} target="_blank" rel="noreferrer">Open original survey source <ExternalLink size={12} /></a>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="findings-empty">
                  <strong>No measured-opinion source is connected.</strong>
                  <p>{result.survey_data_status?.message ?? "This search returned no original survey question and response distribution. OPAL will not manufacture percentages from scholarly abstracts."}</p>
                </div>
              )}
            </section>

            <section className="findings-section">
              <div className="findings-heading">
                <div>
                  <div className="live-kicker">RESEARCH SYNTHESIS</div>
                  <h3>What the evidence tells us</h3>
                </div>
                <span className="findings-count">One evidence brief</span>
              </div>
              {result.findings && result.findings.length > 0 ? (
                <>
                  <p className="findings-intro">
                    {result.evidence_synthesis?.mode === "ai_synthesis"
                      ? "A cross-study synthesis of the retrieved abstracts. Each key point is linked to the source records that support it."
                      : "A transparent extractive brief selecting result-oriented passages across the abstracts, rather than repeating each paper's opening sentence. It does not claim a pooled result."}
                  </p>
                  <article className="evidence-brief-card">
                    <div className="evidence-brief-label">
                      {result.evidence_synthesis?.mode === "ai_synthesis" ? "CROSS-STUDY SUMMARY" : "ABSTRACT-BASED EVIDENCE DIGEST"}
                    </div>
                    <p className="evidence-brief-overview">
                      {result.evidence_synthesis?.overview ?? "Relevant abstracts were found, but no synthesis was returned."}
                    </p>
                    {result.evidence_synthesis?.key_points?.length ? (
                      <ul className="evidence-brief-list">
                        {result.evidence_synthesis.key_points.map((point, index) => {
                          const citedStudies = (point.source_ids ?? [])
                            .map((sourceId) => result.findings?.find((finding) => finding.id === sourceId))
                            .filter((finding): finding is NonNullable<ResearchResult["findings"]>[number] => Boolean(finding));
                          return (
                            <li key={`${point.source_ids.join("-")}-${index}`}>
                              <p>{point.text}</p>
                              {citedStudies.length > 0 ? (
                                <div className="evidence-point-sources">
                                  {citedStudies.map((study) => (
                                    <a href={study.source_url} key={study.id} target="_blank" rel="noreferrer">
                                      {study.source_title}{study.publication_year ? ` · ${study.publication_year}` : ""} <ExternalLink size={12} />
                                    </a>
                                  ))}
                                </div>
                              ) : point.source_url ? (
                                <a href={point.source_url} target="_blank" rel="noreferrer">
                                  {point.source_title ?? "Open supporting study"} <ExternalLink size={12} />
                                </a>
                              ) : null}
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="finding-limitation">The available abstracts did not contain enough result-oriented detail to produce reliable key points. Open the study records below to inspect them.</p>
                    )}
                    {result.evidence_synthesis?.limitations?.map((limitation, index) => (
                      <p className="finding-limitation" key={index}>{limitation}</p>
                    ))}
                  </article>
                </>
              ) : (
                <div className="findings-empty">
                  <strong>No usable abstracts were returned for these matching studies.</strong>
                  <p>OPAL found study records, but their Crossref entries did not include enough abstract text to extract evidence. This is different from finding no research. Open the study records below to inspect available metadata. Survey percentages and measured public-opinion results require dedicated survey sources and are not inferred from publication metadata.</p>
                </div>
              )}
            </section>

            <section className="methodology-results-section">
              <div className="findings-heading">
                <div>
                  <div className="live-kicker">HOW TO READ THESE RESULTS</div>
                  <h3>Methodology</h3>
                </div>
                <span className="findings-count">Evidence standards</span>
              </div>
              <div className="methodology-results-grid">
                {[
                  ["01", "Question relevance", "A record must match the subject and the intent of the question. Generic word overlap is not enough."],
                  ["02", "Measured opinions", "Percentages are shown only when a survey reports the exact question, response counts and respondent base."],
                  ["03", "Source traceability", "Every displayed passage links to the original source record so it can be checked."],
                  ["04", "Evidence types stay separate", "Survey measurements, public discussions and academic background research are never combined into one sample."],
                  ["05", "Limits remain visible", "Missing sample details, fieldwork dates, uncertainty and incomplete abstracts are identified rather than guessed."],
                  ["06", "Denominators matter", "Each percentage is tied to the base for that exact survey question, not automatically to the full study sample."],
                  ["07", "Duplicates are reviewed", "Records are linked when identifiers support the match; uncertain title similarities are flagged instead of silently merged."]
                ].slice(0, visibleMethodology).map(([number, title, description]) => (
                  <article className="methodology-result-card" key={number}>
                    <span>{number}</span>
                    <div><h4>{title}</h4><p>{description}</p></div>
                  </article>
                ))}
              </div>
              {visibleMethodology < 7 && (
                <div className="reveal-controls">
                  {visibleMethodology === 3 ? (
                    <button type="button" onClick={() => setVisibleMethodology(5)}>Show more methodology</button>
                  ) : (
                    <button type="button" onClick={() => setVisibleMethodology(7)}>Show all methodology</button>
                  )}
                </div>
              )}
            </section>

            {result.message && <div className="live-empty">{result.message}</div>}
            {result.studies.length === 0 && !result.message && <div className="live-empty">No publication records were returned. Try a broader topic or different wording.</div>}

            {result.studies.length > 0 && (
              <section className="relevant-studies-section">
                <div className="findings-heading">
                  <div>
                    <div className="live-kicker">SOURCE RECORDS</div>
                    <h3>Relevant studies</h3>
                  </div>
                  <span className="findings-count">{result.studies.length} found</span>
                </div>
                <p className="findings-intro">All {result.studies.length} relevant studies returned by the connected sources are included below. Use the controls to expand the list.</p>
                <div className="study-list">
                {result.studies.slice(0, visibleStudies).map((study, index) => (
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
                {result.studies.length > 3 && visibleStudies < result.studies.length && (
                  <div className="reveal-controls">
                    {visibleStudies === 3 ? (
                      <button type="button" onClick={() => setVisibleStudies(5)}>Show more studies</button>
                    ) : (
                      <button type="button" onClick={() => setVisibleStudies(result.studies.length)}>Show all {result.studies.length} studies</button>
                    )}
                  </div>
                )}
              </section>
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
