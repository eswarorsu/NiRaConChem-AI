"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { ParticleWaveBackground } from "./components/ParticleWaveBackground";

type Recommendation = {
  project_summary: string;
  detected_location: string;
  climate_context: string[];
  recommended_categories: string[];
  application_guidance: string[];
  missing_information: string[];
  ai_recommendation?: string | null;
  ai_precautions?: string[];
  ai_questions?: string[];
  source: string;
  document_name?: string | null;
  document_preview?: string | null;
  rag_sources: string[];
  rag_context: string[];
  best_recommended_system?: string | null;
  best_manufacturer?: string | null;
  recommended_products: Record<string, string>;
  why_recommended: string[];
  supporting_datasheet_references: string[];
  selected_product_profile?: {
    product_name?: string;
    system_type?: string;
    category?: string;
    application_areas?: string[];
    performance?: Record<string, string>;
    score?: number;
  } | null;
};

type FileAnalysis = {
  filename: string;
  file_type: string;
  extracted_characters: number;
  preview: string;
  locations: string[];
  construction_areas: string[];
  requirements: string[];
};

type ClarificationAnswers = {
  area: string;
  exposure: string;
  substrate: string;
  location: string;
  notes: string;
};

const examples = [
  "Basement waterproofing in Dubai",
  "Coastal concrete repair for villa",
  "Rooftop heat exposure waterproofing",
];

const clarificationOptions = {
  area: ["Roof", "Basement", "Wet area", "Parking floor", "Concrete repair", "Expansion joint"],
  exposure: ["UV and heat", "Water pressure", "Coastal chloride", "Vehicle traffic", "Chemical exposure", "Interior use"],
  substrate: ["Concrete", "Screed", "Existing tiles", "Metal", "Blockwork", "Not sure"],
  location: ["Dubai", "Abu Dhabi", "Sharjah", "Coastal UAE", "UAE general"],
};

const broadTerms = ["waterproofing", "flooring", "repair", "coating", "sealant", "tile adhesive", "chemical"];
const areaTerms = ["roof", "rooftop", "basement", "bathroom", "wet", "parking", "floor", "joint", "tank", "pool", "wall", "slab", "villa"];
const exposureTerms = ["uv", "heat", "traffic", "chemical", "chloride", "coastal", "water", "pressure", "potable", "external", "interior", "crack"];
const substrateTerms = ["concrete", "screed", "tile", "metal", "block", "masonry", "plaster"];

function displayValue(value?: string | null) {
  return value && value.trim() ? value : "Not specified in retrieved datasheet";
}

function includesAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term));
}

function shouldAskClarifyingQuestions(value: string, hasFileContext: boolean) {
  const normalized = value.toLowerCase().trim();
  const words = normalized.split(/\s+/).filter(Boolean);
  const isBroadCategory = broadTerms.some((term) => normalized === term || normalized === `${term} chemicals`);
  const missingArea = !includesAny(normalized, areaTerms);
  const missingExposure = !includesAny(normalized, exposureTerms);
  const missingSubstrate = !includesAny(normalized, substrateTerms);
  const missingCount = [missingArea, missingExposure, missingSubstrate].filter(Boolean).length;

  return !hasFileContext && (isBroadCategory || words.length <= 3 || missingCount >= 2);
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [fileAnalysis, setFileAnalysis] = useState<FileAnalysis | null>(null);
  const [showClarifier, setShowClarifier] = useState(false);
  const [clarification, setClarification] = useState<ClarificationAnswers>({
    area: "",
    exposure: "",
    substrate: "",
    location: "",
    notes: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzingFile, setIsAnalyzingFile] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setIsDarkTheme(localStorage.getItem("niraconchem-theme") === "dark");
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("theme-dark-body", isDarkTheme);
    document.body.classList.toggle("theme-dark-body", isDarkTheme);
  }, [isDarkTheme]);

  function toggleTheme() {
    setIsDarkTheme((current) => {
      const next = !current;
      localStorage.setItem("niraconchem-theme", next ? "dark" : "light");
      return next;
    });
  }

  function updateClarification(key: keyof ClarificationAnswers, value: string) {
    setClarification((current) => ({
      ...current,
      [key]: current[key] === value && key !== "notes" ? "" : value,
    }));
  }

  function buildClarifiedQuery() {
    const details = [
      clarification.area ? `construction area: ${clarification.area}` : "",
      clarification.exposure ? `exposure: ${clarification.exposure}` : "",
      clarification.substrate ? `substrate: ${clarification.substrate}` : "",
      clarification.location ? `location: ${clarification.location}` : "",
      clarification.notes ? `additional details: ${clarification.notes}` : "",
    ].filter(Boolean);

    return details.length ? `${query.trim()}. ${details.join("; ")}.` : query.trim();
  }

  async function submitRecommendation(nextQuery = query) {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) {
      setError("Enter a construction chemical requirement first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setShowClarifier(false);

    try {
      const response = await fetch("http://localhost:8000/recommend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: trimmedQuery,
          document_context: fileAnalysis?.preview,
          document_name: fileAnalysis?.filename,
        }),
      });

      if (!response.ok) {
        throw new Error("Recommendation request failed.");
      }

      const data = (await response.json()) as Recommendation;
      setRecommendation(data);
      if (nextQuery !== query) {
        setQuery(nextQuery);
      }
    } catch {
      setError("Backend is not reachable. Start the API server and try again.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Enter a construction chemical requirement first.");
      return;
    }

    if (shouldAskClarifyingQuestions(trimmedQuery, Boolean(fileAnalysis)) && !showClarifier) {
      setRecommendation(null);
      setError("");
      setShowClarifier(true);
      return;
    }

    void submitRecommendation(showClarifier ? buildClarifiedQuery() : trimmedQuery);
  }

  function handleExample(example: string) {
    setQuery(example);
    setShowClarifier(false);
    void submitRecommendation(example);
  }

  function submitWithClarification() {
    void submitRecommendation(buildClarifiedQuery());
  }

  function skipClarification() {
    void submitRecommendation(query);
  }

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setIsAnalyzingFile(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("http://localhost:8000/analyze-file", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("File analysis failed.");
      }

      const data = (await response.json()) as FileAnalysis;
      setFileAnalysis(data);
    } catch {
      setError("Could not read that file. Try PDF, DOCX, XLSX, or TXT under 10 MB.");
      setFileAnalysis(null);
    } finally {
      setIsAnalyzingFile(false);
      event.target.value = "";
    }
  }

  function clearFileAnalysis() {
    setFileAnalysis(null);
  }

  async function downloadReport() {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Generate a recommendation before downloading a PDF.");
      return;
    }

    setIsDownloading(true);
    setError("");

    try {
      const response = await fetch("http://localhost:8000/recommend/report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: trimmedQuery,
          document_context: fileAnalysis?.preview,
          document_name: fileAnalysis?.filename,
        }),
      });

      if (!response.ok) {
        throw new Error("PDF request failed.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "niraconchem-recommendation.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not download the PDF report. Check that the backend is running.");
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <main className={`home${recommendation ? " has-result" : ""}${isDarkTheme ? " dark-theme" : ""}`}>
      <button
        aria-label={isDarkTheme ? "Switch to light theme" : "Switch to dark theme"}
        className="theme-toggle"
        onClick={toggleTheme}
        title={isDarkTheme ? "Light theme" : "Dark theme"}
        type="button"
      >
        <span className="theme-toggle-symbol theme-toggle-sun" aria-hidden="true">☀</span>
        <span className="theme-toggle-symbol theme-toggle-moon" aria-hidden="true">☾</span>
        <span className="theme-toggle-knob" aria-hidden="true" />
      </button>
      <ParticleWaveBackground />
      <header className="topbar">
        <div className="logo-card" aria-label="NIRACONCHEM chemistry logo">
          <img
            className="atom-logo"
            src="/assets/atom-logo-transparent.png.png"
            alt="NIRACONCHEM chemistry logo"
          />
        </div>
        <p className="assistant-label">Ask for UAE-ready construction chemical guidance</p>
      </header>

      <section className={`search-stage${recommendation ? " has-result" : ""}`} aria-label="Construction chemicals search">
        <form className="search-box" onSubmit={handleSubmit}>
          <label className="upload-icon-button" htmlFor="project-file" title="Upload project file">
            📎
          </label>
          <input
            accept=".pdf,.docx,.xlsx,.txt"
            disabled={isAnalyzingFile}
            id="project-file"
            onChange={handleFileUpload}
            type="file"
          />
          <input
            aria-label="Construction chemical recommendation query"
            className="query-input"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search: waterproofing for Dubai basement, tile adhesive for pool, repair mortar for coastal villa..."
            type="search"
            value={query}
          />
          <button disabled={isLoading} type="submit">
            {isLoading ? "Checking" : "Search"}
          </button>
        </form>
        <div className="quick-prompts" aria-label="Example searches">
          {examples.map((example) => (
            <button key={example} onClick={() => handleExample(example)} type="button">
              {example}
            </button>
          ))}
        </div>

        {showClarifier ? (
          <div className="clarifier-panel" aria-label="Project clarification questions">
            <div className="clarifier-header">
              <span>Project details</span>
              <p>Add a few details so the agent can match the datasheets more accurately.</p>
            </div>
            <div className="clarifier-grid">
              <section>
                <h3>Construction area</h3>
                <div className="clarifier-options">
                  {clarificationOptions.area.map((option) => (
                    <button
                      className={clarification.area === option ? "selected" : ""}
                      key={option}
                      onClick={() => updateClarification("area", option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </section>
              <section>
                <h3>Exposure condition</h3>
                <div className="clarifier-options">
                  {clarificationOptions.exposure.map((option) => (
                    <button
                      className={clarification.exposure === option ? "selected" : ""}
                      key={option}
                      onClick={() => updateClarification("exposure", option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </section>
              <section>
                <h3>Substrate</h3>
                <div className="clarifier-options">
                  {clarificationOptions.substrate.map((option) => (
                    <button
                      className={clarification.substrate === option ? "selected" : ""}
                      key={option}
                      onClick={() => updateClarification("substrate", option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </section>
              <section>
                <h3>Project location</h3>
                <div className="clarifier-options">
                  {clarificationOptions.location.map((option) => (
                    <button
                      className={clarification.location === option ? "selected" : ""}
                      key={option}
                      onClick={() => updateClarification("location", option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </section>
            </div>
            <textarea
              aria-label="Additional project notes"
              className="clarifier-notes"
              onChange={(event) => updateClarification("notes", event.target.value)}
              placeholder="Optional: add thickness, crack width, new/old concrete, traffic level, water pressure, or specification requirement..."
              value={clarification.notes}
            />
            <div className="clarifier-actions">
              <button disabled={isLoading} onClick={submitWithClarification} type="button">
                Recommend with details
              </button>
              <button disabled={isLoading} onClick={skipClarification} type="button">
                Skip questions
              </button>
            </div>
          </div>
        ) : null}

        {fileAnalysis ? (
          <div className="file-summary">
            <div>
              <strong>{fileAnalysis.filename}</strong>
              <span>{fileAnalysis.extracted_characters} characters extracted</span>
            </div>
            <button onClick={clearFileAnalysis} type="button">
              Remove
            </button>
            <p>{fileAnalysis.preview}</p>
            <ul>
              {[...fileAnalysis.locations, ...fileAnalysis.construction_areas, ...fileAnalysis.requirements]
                .slice(0, 8)
                .map((item) => (
                  <li key={item}>{item}</li>
                ))}
            </ul>
          </div>
        ) : null}

        {error ? <p className="error-text">{error}</p> : null}

        {recommendation ? (
          <article className="result-panel report-preview">
            <div className="result-header">
              <p>NIRACONCHEM AI Technical Recommendation Report</p>
              <span>PDF Preview</span>
            </div>
            <button className="download-button" disabled={isDownloading} onClick={downloadReport} type="button">
              {isDownloading ? "Preparing PDF" : "Download PDF"}
            </button>

            <section className="report-section">
              <h3>1. Project Information</h3>
              <div className="report-table">
                <div><strong>Project Query</strong><span>{query}</span></div>
                <div><strong>Project Type</strong><span>{recommendation.selected_product_profile?.category || recommendation.recommended_categories[0] || "Construction chemical recommendation"}</span></div>
                <div><strong>Project Area</strong><span>{recommendation.selected_product_profile?.application_areas?.join(", ") || "Not specified"}</span></div>
                <div><strong>Detected Location</strong><span>{recommendation.detected_location}</span></div>
                <div><strong>Recommendation Source</strong><span>AI + Vector Database + Technical Datasheets</span></div>
              </div>
            </section>

            <section className="report-section">
              <h3>2. Project Condition Assessment</h3>
              <p>{recommendation.project_summary}</p>
              <ul>
                {recommendation.climate_context.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            <section className="report-section">
              <h3>3. Recommended System</h3>
              <div className="report-table">
                <div><strong>System Name</strong><span>{displayValue(recommendation.best_recommended_system)}</span></div>
                <div><strong>System Category</strong><span>{recommendation.selected_product_profile?.category || recommendation.recommended_categories[0]}</span></div>
                <div><strong>Recommended Manufacturer</strong><span>{displayValue(recommendation.best_manufacturer)}</span></div>
                <div><strong>Confidence Score</strong><span>{recommendation.selected_product_profile?.score ? `${recommendation.selected_product_profile.score}/10` : "Datasheet profile matched"}</span></div>
              </div>
            </section>

            <section className="report-section">
              <h3>4. Recommended Products</h3>
              <div className="product-preview">
                <div><strong>Primer</strong><span>{displayValue(recommendation.recommended_products?.primer)}</span></div>
                <div><strong>Main Product</strong><span>{displayValue(recommendation.recommended_products?.main_membrane)}</span></div>
                <div><strong>Reinforcement</strong><span>{displayValue(recommendation.recommended_products?.reinforcement)}</span></div>
                <div><strong>Top Coat</strong><span>{displayValue(recommendation.recommended_products?.top_coat)}</span></div>
              </div>
            </section>

            <section className="report-section">
              <h3>5. Technical Justification</h3>
              <ul>
                {(recommendation.why_recommended.length ? recommendation.why_recommended : ["System selected from matching datasheet profile."]).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            <section className="report-section">
              <h3>6. Product Performance Data</h3>
              <div className="report-table">
                {Object.entries(recommendation.selected_product_profile?.performance || {}).length ? (
                  Object.entries(recommendation.selected_product_profile?.performance || {}).map(([key, value]) => (
                    <div key={key}><strong>{key.replaceAll("_", " ")}</strong><span>{value}</span></div>
                  ))
                ) : (
                  <div><strong>Performance</strong><span>Verify final values in manufacturer datasheet.</span></div>
                )}
              </div>
            </section>

            <section className="report-section">
              <h3>7. Application System</h3>
              <ol>
                <li>Surface preparation</li>
                <li>Primer application where specified</li>
                <li>Main product application</li>
                <li>Reinforcement or detailing where required</li>
                <li>Top coat or finishing layer where specified</li>
                <li>Curing and final inspection</li>
              </ol>
            </section>

            <section className="report-section">
              <h3>8. Application Guidance</h3>
              <ul>
                {recommendation.application_guidance.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            <section className="report-section">
              <h3>9. Quality Assurance Requirements</h3>
              <ul>
                <li>Verify substrate condition before application.</li>
                <li>Use manufacturer-approved application method and trained applicator.</li>
                <li>Confirm coverage, thickness, curing, and adhesion before handover.</li>
              </ul>
            </section>

            <section className="report-section">
              <h3>10. Safety Precautions</h3>
              <ul>
                {(recommendation.ai_precautions?.length ? recommendation.ai_precautions : [
                  "Use PPE during application.",
                  "Ensure adequate ventilation.",
                  "Follow manufacturer SDS requirements.",
                ]).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            <section className="report-section">
              <h3>11. Missing Information</h3>
              {recommendation.missing_information.length ? (
                <ul>
                  {recommendation.missing_information.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p>No major missing information detected from the provided project details.</p>
              )}
            </section>

            <section className="report-section">
              <h3>12. Datasheet References</h3>
              <p>Recommendation is based on matched technical datasheet profiles and retrieved product evidence. Detailed references are included in the downloaded PDF.</p>
            </section>

            <section className="report-section">
              <h3>13. Alternative Manufacturers</h3>
              <p>Approved equal systems may be considered only after matching datasheet performance, application area, and project specification requirements.</p>
            </section>

            <section className="report-section">
              <h3>14. Final Recommendation</h3>
              <p>{recommendation.ai_recommendation || `Use ${displayValue(recommendation.best_recommended_system)} from ${displayValue(recommendation.best_manufacturer)} after confirming substrate, exposure, and project specification requirements.`}</p>
            </section>

            <section className="report-section muted-report-section">
              <h3>15. Disclaimer</h3>
              <p>This preview provides preliminary technical guidance based on available project information, vector database retrieval, technical datasheets, and AI-assisted analysis. Final product selection must be verified through site inspection, project specifications, manufacturer datasheets, method statements, and applicable local standards.</p>
            </section>
          </article>
        ) : null}
      </section>
    </main>
  );
}
