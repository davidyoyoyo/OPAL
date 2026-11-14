"use client";

import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Check,
  ChevronDown,
  CircleHelp,
  Database,
  Download,
  FileSpreadsheet,
  Filter,
  Globe2,
  Info,
  MessageSquare,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Table2,
} from "lucide-react";
import { useSearchParams } from "next/navigation";

type EvidenceRow = {
  id: number;
  response: string;
  share: number;
  evidence: "Survey" | "Discussion" | "Research";
  source: string;
  geography: string;
  year: number;
};

const rows: EvidenceRow[] = [
  { id: 1, response: "Strongly support", share: 42, evidence: "Survey", source: "Illustrative national opinion poll", geography: "Example population", year: 2025 },
  { id: 2, response: "Somewhat support", share: 26, evidence: "Survey", source: "Illustrative national opinion poll", geography: "Example population", year: 2025 },
  { id: 3, response: "Neither support nor oppose", share: 14, evidence: "Survey", source: "Illustrative national opinion poll", geography: "Example population", year: 2025 },
  { id: 4, response: "Oppose", share: 18, evidence: "Survey", source: "Illustrative national opinion poll", geography: "Example population", year: 2025 },
  { id: 5, response: "More time for family", share: 31, evidence: "Discussion", source: "Example public discussion theme", geography: "Online discussion", year: 2025 },
  { id: 6, response: "Concern about workload compression", share: 24, evidence: "Discussion", source: "Example public discussion theme", geography: "Online discussion", year: 2025 },
  { id: 7, response: "Potential productivity changes", share: 45, evidence: "Research", source: "Example workplace research topic", geography: "Multi-country context", year: 2024 },
];

const evidenceColors: Record<EvidenceRow["evidence"], string> = {
  Survey: "survey",
  Discussion: "discussion",
  Research: "research",
};

export default function ResearchPage() {
  const searchParams = useSearchParams();
  const question = searchParams.get("q") || "Should the working week be four days?";
  const [activeTab, setActiveTab] = useState<"overview" | "evidence">("overview");
  const [evidenceFilter, setEvidenceFilter] = useState("All evidence");
  const [search, setSearch] = useState("");
  const [showMethodology, setShowMethodology] = useState(false);

  const filteredRows = useMemo(() => rows.filter((row) => {
    const matchesType = evidenceFilter === "All evidence" || row.evidence === evidenceFilter;
    const matchesSearch = (row.response + " " + row.source + " " + row.evidence).toLowerCase().includes(search.toLowerCase());
    return matchesType && matchesSearch;
  }), [evidenceFilter, search]);

  function exportCsv() {
    const header = ["Response or theme", "Value (%)", "Evidence type", "Source description", "Geography", "Year"];
    const csvRows = filteredRows.map((row) => [row.response, row.share, row.evidence, row.source, row.geography, row.year]);
    const csv = [header, ...csvRows].map((line) => line.map((value) => '"' + String(value).replaceAll('"', '""') + '"').join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "opal-example-evidence.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="workspace-page">
      <aside className="workspace-sidebar">
        <a className="brand workspace-brand" href="/">
          <span className="brand-mark"><span /></span>
          <span>opal<span className="brand-period">.</span></span>
        </a>
        <div className="sidebar-label">WORKSPACE</div>
        <a className="sidebar-link active" href="/"><Search size={16} /> New research</a>
        <a className="sidebar-link" href="/#methodology"><BookOpen size={16} /> Methodology</a>
        <div className="sidebar-bottom">
          <div className="sidebar-note-icon"><ShieldCheck size={16} /></div>
          <strong>Research with context</strong>
          <p>Evidence types are kept separate so results aren't misleading.</p>
          <a href="/#methodology">Our principles <ArrowUpRight size={12} /></a>
        </div>
      </aside>

      <section className="workspace-main">
        <header className="workspace-header">
          <div className="breadcrumbs"><a href="/">OPAL</a><span>/</span><span>Research workspace</span></div>
          <div className="workspace-header-right"><span className="no-account"><span className="privacy-dot" /> No account required</span><a href="/">New question <ArrowUpRight size={14} /></a></div>
        </header>

        <div className="workspace-content">
          <div className="workspace-title-row">
            <div>
              <div className="workspace-kicker">RESEARCH OUTPUT <span className="demo-label">DEMO DATA</span></div>
              <h1>{question}</h1>
              <p className="workspace-subtitle">An example of how OPAL will organise findings, sources and supporting context.</p>
            </div>
            <button className="export-button" onClick={exportCsv}><Download size={15} /> Export CSV</button>
          </div>

          <div className="demo-warning"><Info size={15} /><span><strong>Illustrative data only.</strong> This workspace demonstrates the intended interface. These figures are not real survey findings and must not be used as evidence.</span></div>

          <div className="workspace-tabs">
            <button className={activeTab === "overview" ? "selected" : ""} onClick={() => setActiveTab("overview")}><BarChart3 size={15} /> Overview</button>
            <button className={activeTab === "evidence" ? "selected" : ""} onClick={() => setActiveTab("evidence")}><Table2 size={15} /> Evidence table <span className="tab-count">7</span></button>
          </div>

          {activeTab === "overview" ? (
            <>
              <div className="stat-grid">
                <article className="stat-card"><span>ILLUSTRATIVE SUPPORT</span><strong>68%</strong><small><span className="stat-mark">↗</span> Survey example only</small></article>
                <article className="stat-card"><span>EVIDENCE ITEMS</span><strong>07</strong><small>Across 3 evidence types</small></article>
                <article className="stat-card"><span>TIME COVERED</span><strong>2024–25</strong><small>Example date range</small></article>
                <article className="stat-card"><span>GEOGRAPHIC SCOPE</span><strong>Mixed</strong><small>Not a single population</small></article>
              </div>

              <div className="workspace-grid">
                <section className="panel opinion-panel">
                  <div className="panel-heading"><div><span className="panel-kicker">01 / SURVEY MEASUREMENT</span><h2>Illustrative response distribution</h2></div><span className="panel-menu">EXAMPLE</span></div>
                  <p className="panel-description">The four response categories below represent a hypothetical survey distribution.</p>
                  <div className="distribution">
                    {[
                      ["Strongly support", 42, "#34795A"],
                      ["Somewhat support", 26, "#8FB7A0"],
                      ["Neither / unsure", 14, "#C7D3CA"],
                      ["Oppose", 18, "#D5A69B"],
                    ].map(([label, value, color]) => (
                      <div className="distribution-row" key={String(label)}>
                        <div className="distribution-label"><span>{label}</span><strong>{value}%</strong></div>
                        <div className="distribution-track"><div style={{ width: String(value) + "%", background: String(color) }} /></div>
                      </div>
                    ))}
                  </div>
                  <div className="panel-footnote"><Info size={13} /> A real result would show sample size, field dates, population and methodology.</div>
                </section>

                <section className="panel evidence-panel">
                  <div className="panel-heading"><div><span className="panel-kicker">02 / EVIDENCE LANDSCAPE</span><h2>What the sources contribute</h2></div><span className="panel-menu">3 TYPES</span></div>
                  <div className="evidence-type-card"><div className="evidence-icon survey-icon"><BarChart3 size={16} /></div><div><strong>Measured opinions</strong><span>Surveys and polls with defined samples</span></div><b>04</b></div>
                  <div className="evidence-type-card"><div className="evidence-icon discussion-icon"><MessageSquare size={16} /></div><div><strong>Expressed opinions</strong><span>Public discussions and arguments</span></div><b>02</b></div>
                  <div className="evidence-type-card"><div className="evidence-icon research-icon"><BookOpen size={16} /></div><div><strong>Supporting research</strong><span>Studies that add context, not vote counts</span></div><b>01</b></div>
                  <div className="separation-note"><ShieldCheck size={14} /> These evidence types are never combined into one sample.</div>
                </section>
              </div>

              <section className="panel preview-table-panel">
                <div className="panel-heading"><div><span className="panel-kicker">03 / STRUCTURED DATA</span><h2>Evidence at a glance</h2></div><button className="text-action" onClick={() => setActiveTab("evidence")}>View all evidence <ArrowUpRight size={13} /></button></div>
                <EvidenceTable data={rows.slice(0, 4)} />
              </section>
            </>
          ) : (
            <section className="panel full-evidence-panel">
              <div className="panel-heading"><div><span className="panel-kicker">SOURCE-LEVEL DATA</span><h2>Evidence table</h2><p className="panel-description">Each row retains its evidence type and source context. Percentages from different evidence types are not directly comparable.</p></div></div>
              <div className="table-controls">
                <label className="table-search"><Search size={15} /><input value={search} onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)} placeholder="Search evidence..." /></label>
                <label className="filter-select"><Filter size={14} /><select value={evidenceFilter} onChange={(event) => setEvidenceFilter(event.target.value)}><option>All evidence</option><option>Survey</option><option>Discussion</option><option>Research</option></select><ChevronDown size={13} /></label>
                <button className="small-export" onClick={exportCsv}><ArrowDownToLine size={14} /> Download CSV</button>
              </div>
              <EvidenceTable data={filteredRows} />
              <div className="table-result-count">Showing {filteredRows.length} of {rows.length} illustrative evidence items</div>
            </section>
          )}

          <div className="methodology-toggle">
            <button onClick={() => setShowMethodology(!showMethodology)}><CircleHelp size={15} /> How should I interpret this? <ChevronDown className={showMethodology ? "rotated" : ""} size={14} /></button>
            {showMethodology && <p>In a live OPAL report, each survey result would be tied to its population, sample size, field dates and methodology. Public discussion themes would be presented separately and would not be treated as representative polling. Supporting research would provide context rather than be counted as public opinion.</p>}
          </div>

          <footer className="workspace-footer"><span>OPAL · Opinion research, made clear.</span><span><ShieldCheck size={13} /> Evidence provenance matters</span></footer>
        </div>
      </section>
    </main>
  );
}

function EvidenceTable({ data }: { data: EvidenceRow[] }) {
  return (
    <div className="evidence-table-wrap">
      <table className="evidence-table">
        <thead><tr><th>RESPONSE / THEME</th><th>VALUE</th><th>EVIDENCE TYPE</th><th>SOURCE</th><th>YEAR</th></tr></thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.id}>
              <td className="response-cell">{row.response}</td>
              <td className="value-cell">{row.share}%</td>
              <td><span className={"evidence-badge " + evidenceColors[row.evidence]}>{row.evidence}</span></td>
              <td className="source-cell">{row.source}</td>
              <td className="year-cell">{row.year}</td>
            </tr>
          ))}
          {data.length === 0 && <tr><td colSpan={5} className="empty-table">No matching evidence. Try a different search or filter.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
