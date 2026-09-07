import { useState } from "react";
import { uploadContract } from "./services/api";

function App() {
  const [file, setFile] = useState(null);
  const [screen, setScreen] = useState("upload");
  const [analysisResults, setAnalysisResults] = useState(null);
  const [error, setError] = useState("");

  /*
   * =========================================================
   * FILE SELECTION
   * =========================================================
   */

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (!selectedFile) {
      return;
    }

    const fileName = selectedFile.name.toLowerCase();

    const isPDF = fileName.endsWith(".pdf");
    const isDOCX = fileName.endsWith(".docx");

    if (!isPDF && !isDOCX) {
      setError("Please upload a PDF or DOCX contract.");
      setFile(null);
      event.target.value = "";
      return;
    }

    setError("");
    setFile(selectedFile);
  };


  /*
   * =========================================================
   * CONTRACT ANALYSIS
   * =========================================================
   *
   * IMPORTANT:
   * There is NO mock-data fallback.
   *
   * If the backend fails, the user sees the real error.
   */

  const analyzeContract = async () => {
    if (!file) {
      setError("Please select a contract first.");
      return;
    }

    setError("");
    setScreen("processing");

    try {
      const result = await uploadContract(file);

      console.log("Real backend analysis result:", result);

      setAnalysisResults(result);
      setScreen("results");
    } catch (err) {
      console.error("Contract analysis error:", err);

      setError(
        err?.message ||
          "Unable to analyze the contract. Please make sure the backend is running."
      );

      setScreen("upload");
    }
  };


  /*
   * =========================================================
   * RESET
   * =========================================================
   */

  const resetAnalysis = () => {
    setFile(null);
    setError("");
    setAnalysisResults(null);
    setScreen("upload");
  };


  /*
   * =========================================================
   * HELPER FUNCTIONS
   * =========================================================
   */

  const getRiskClass = (level) => {
    if (!level) {
      return "normal";
    }

    const normalized = String(level).toLowerCase();

    if (normalized.includes("high")) {
      return "high";
    }

    if (normalized.includes("medium")) {
      return "medium";
    }

    if (normalized.includes("low")) {
      return "low";
    }

    return "normal";
  };


  const formatConfidence = (confidence) => {
    if (confidence === undefined || confidence === null) {
      return "N/A";
    }

    const value = Number(confidence);

    if (Number.isNaN(value)) {
      return "N/A";
    }

    return `${Math.round(value * 100)}%`;
  };


  const formatRiskScore = (score) => {
    if (score === undefined || score === null) {
      return "0.0";
    }

    const value = Number(score);

    if (Number.isNaN(value)) {
      return "0.0";
    }

    return value.toFixed(1);
  };


  const getRiskDescription = (level) => {
    const normalized = String(level || "").toLowerCase();

    if (normalized.includes("high")) {
      return "High-risk areas require priority legal review.";
    }

    if (normalized.includes("medium")) {
      return "Moderate-risk areas may require additional review.";
    }

    if (normalized.includes("low")) {
      return "No major high-risk indicators were detected.";
    }

    return "Review the detected findings before making a decision.";
  };


  /*
   * =========================================================
   * UPLOAD SCREEN
   * =========================================================
   */

  const renderUploadScreen = () => {
    return (
      <main className="main-content">

        <section className="hero">

          <div className="hero-text">

            <span className="eyebrow">
              AI-POWERED CONTRACT INTELLIGENCE
            </span>

            <h2>
              Review contracts.
              <br />

              <span>
                Identify risk faster.
              </span>
            </h2>

            <p>
              Automatically identify legal clauses,
              extract important entities, and surface
              potential contract risks using intelligent
              NLP analysis.
            </p>

            <div className="hero-points">

              <div>
                <span>✓</span>
                Clause detection
              </div>

              <div>
                <span>✓</span>
                Entity extraction
              </div>

              <div>
                <span>✓</span>
                AI risk assessment
              </div>

            </div>

          </div>


          <div className="upload-card">

            <div className="upload-icon">
              ↑
            </div>

            <h3>
              Upload your contract
            </h3>

            <p>
              Select a legal contract to begin
              automated analysis.
            </p>


            <label className="upload-button">

              Choose Contract

              <input
                type="file"
                accept=".pdf,.docx"
                onChange={handleFileChange}
              />

            </label>


            {error && (
              <div className="upload-error">
                {error}
              </div>
            )}


            {file && (

              <div className="selected-file">

                <div className="file-info">

                  <span className="file-icon">
                    {file.name
                      .toLowerCase()
                      .endsWith(".pdf")
                      ? "PDF"
                      : "DOCX"}
                  </span>

                  <div>

                    <strong>
                      {file.name}
                    </strong>

                    <small>
                      Ready for analysis
                    </small>

                  </div>

                </div>


                <button
                  className="analyze-button"
                  onClick={analyzeContract}
                >
                  Analyze Contract →
                </button>

              </div>

            )}


            <small className="supported">
              Supported formats: PDF and DOCX
            </small>

          </div>

        </section>


        <section className="feature-section">

          <div className="section-title">

            <span>
              WHAT THE SYSTEM ANALYZES
            </span>

            <h3>
              From document to actionable insight.
            </h3>

          </div>


          <div className="features">

            <div className="feature-card">

              <div className="feature-top">

                <span className="feature-number">
                  01
                </span>

                <span className="feature-icon">
                  NLP
                </span>

              </div>

              <h3>
                Entity Extraction
              </h3>

              <p>
                Identify parties, dates,
                jurisdictions, monetary values,
                and other important contract entities.
              </p>

            </div>


            <div className="feature-card">

              <div className="feature-top">

                <span className="feature-number">
                  02
                </span>

                <span className="feature-icon">
                  AI
                </span>

              </div>

              <h3>
                Clause Analysis
              </h3>

              <p>
                Detect termination,
                confidentiality,
                indemnification,
                intellectual property,
                and renewal clauses.
              </p>

            </div>


            <div className="feature-card">

              <div className="feature-top">

                <span className="feature-number">
                  03
                </span>

                <span className="feature-icon">
                  RISK
                </span>

              </div>

              <h3>
                Risk Scoring
              </h3>

              <p>
                Surface potentially unfavorable
                language and prioritize areas
                requiring legal review.
              </p>

            </div>

          </div>

        </section>

      </main>
    );
  };


  /*
   * =========================================================
   * PROCESSING SCREEN
   * =========================================================
   */

  const renderProcessingScreen = () => {
    return (
      <main className="processing-page">

        <div className="processing-card">

          <div className="processing-icon">

            <div className="spinner"></div>

          </div>

          <span className="eyebrow">
            AI ANALYSIS
          </span>

          <h2>
            Analyzing your contract
          </h2>

          <p>
            Extracting entities, identifying legal
            clauses, and evaluating potential risk
            factors using the Contract Intelligence
            NLP pipeline.
          </p>

          <div className="processing-file">
            {file?.name}
          </div>

          <div className="processing-progress">

            <div className="progress-bar"></div>

          </div>

          <div className="processing-steps">

            <span>
              ✓ Document received
            </span>

            <span>
              ✓ Text extraction
            </span>

            <span>
              • Legal-BERT analysis in progress
            </span>

          </div>

        </div>

      </main>
    );
  };


  /*
   * =========================================================
   * RESULTS DASHBOARD
   * =========================================================
   */

  const renderResultsScreen = () => {

    if (!analysisResults) {
      return (
        <main className="dashboard">

          <div className="dashboard-card">

            <h3>
              No analysis results available.
            </h3>

            <button
              className="new-analysis-button"
              onClick={resetAnalysis}
            >
              + New Analysis
            </button>

          </div>

        </main>
      );
    }


    const riskScore = Number(
      analysisResults.risk_score || 0
    );

    const riskLevel =
      analysisResults.risk_level || "UNKNOWN";

    const entities =
      Array.isArray(analysisResults.entities)
        ? analysisResults.entities
        : [];

    const clauses =
      Array.isArray(analysisResults.clauses)
        ? analysisResults.clauses
        : [];

    const findings =
      Array.isArray(analysisResults.findings)
        ? analysisResults.findings
        : [];


    return (
      <main className="dashboard">

        {/* =================================================
            DASHBOARD HEADER
        ================================================= */}

        <div className="dashboard-header">

          <div>

            <span className="eyebrow">
              CONTRACT ANALYSIS COMPLETE
            </span>

            <h2>
              Risk Overview
            </h2>

            <p>
              {analysisResults.contract_name ||
                file?.name ||
                "Contract"}
            </p>

          </div>


          <button
            className="new-analysis-button"
            onClick={resetAnalysis}
          >
            + New Analysis
          </button>

        </div>


        {/* =================================================
            SUMMARY CARDS
        ================================================= */}

        <section className="summary-grid">

          <div className="risk-card">

            <div>

              <span className="card-label">
                OVERALL CONTRACT RISK
              </span>

              <div className="risk-score">

                {formatRiskScore(riskScore)}

                <span>
                  /100
                </span>

              </div>

              <span
                className={`high-risk-label ${getRiskClass(
                  riskLevel
                )}`}
              >
                {riskLevel}
              </span>

              <p>
                {getRiskDescription(riskLevel)}
              </p>

            </div>


            <div className="risk-gauge">

              <div className="gauge-inner">

                <strong>
                  {Math.round(riskScore)}
                </strong>

                <span>
                  Risk Score
                </span>

              </div>

            </div>

          </div>


          <div className="summary-card">

            <span className="card-label">
              ENTITIES
            </span>

            <strong>
              {entities.length}
            </strong>

            <p>
              Key entities identified
            </p>

          </div>


          <div className="summary-card">

            <span className="card-label">
              CLAUSES
            </span>

            <strong>
              {clauses.length}
            </strong>

            <p>
              Legal clauses detected
            </p>

          </div>


          <div className="summary-card">

            <span className="card-label">
              RISK FINDINGS
            </span>

            <strong>
              {findings.length}
            </strong>

            <p>
              Items requiring review
            </p>

          </div>

        </section>


        {/* =================================================
            ENTITIES + FINDINGS
        ================================================= */}

        <section className="dashboard-grid">

          {/* ENTITIES */}

          <div className="dashboard-card">

            <div className="section-heading">

              <div>

                <span className="card-label">
                  NER
                </span>

                <h3>
                  Extracted Entities
                </h3>

              </div>

              <span className="count-badge">
                {entities.length}
              </span>

            </div>


            <div className="entity-list">

              {entities.length === 0 ? (

                <div className="empty-state">
                  No entities were detected.
                </div>

              ) : (

                entities.map((entity, index) => (

                  <div
                    className="entity-row"
                    key={`${entity.label}-${index}`}
                  >

                    <span>
                      {entity.label || "ENTITY"}
                    </span>

                    <strong>
                      {entity.value || "—"}
                    </strong>

                  </div>

                ))

              )}

            </div>

          </div>


          {/* FINDINGS */}

          <div className="dashboard-card">

            <div className="section-heading">

              <div>

                <span className="card-label">
                  AI REVIEW
                </span>

                <h3>
                  Risk Findings
                </h3>

              </div>

              <span className="count-badge red">
                {findings.length}
              </span>

            </div>


            <div className="finding-list">

              {findings.length === 0 ? (

                <div className="empty-state">
                  No risk findings were returned by the
                  analysis pipeline.
                </div>

              ) : (

                findings.map((finding, index) => (

                  <div
                    className="finding"
                    key={`${finding.title || "finding"}-${index}`}
                  >

                    <span
                      className={`risk-badge ${getRiskClass(
                        finding.level
                      )}`}
                    >
                      {finding.level || "REVIEW"}
                    </span>

                    <div>

                      <strong>
                        {finding.title ||
                          finding.name ||
                          "Risk Finding"}
                      </strong>

                      <p>
                        {finding.description ||
                          finding.text ||
                          "Potential risk identified by the analysis pipeline."}
                      </p>

                      {finding.confidence !== undefined && (

                        <small>
                          Confidence:{" "}
                          {formatConfidence(
                            finding.confidence
                          )}
                        </small>

                      )}

                    </div>

                  </div>

                ))

              )}

            </div>

          </div>

        </section>


        {/* =================================================
            CLAUSES
        ================================================= */}

        <section className="dashboard-card clauses-card">

          <div className="section-heading">

            <div>

              <span className="card-label">
                CLAUSE CLASSIFICATION
              </span>

              <h3>
                Detected Legal Clauses
              </h3>

            </div>

            <span className="count-badge">
              {clauses.length}
            </span>

          </div>


          <div className="clause-grid">

            {clauses.length === 0 ? (

              <div className="empty-state">
                No legal clauses were detected.
              </div>

            ) : (

              clauses.map((clause, index) => {

                const clauseStatus =
                  clause.status ||
                  clause.risk_level ||
                  "Detected";

                const clauseClass =
                  getRiskClass(clauseStatus);

                return (

                  <div
                    className="clause-card"
                    key={`${clause.name || "clause"}-${index}`}
                  >

                    <div className="clause-top">

                      <h4>
                        {clause.name ||
                          "Legal Clause"}
                      </h4>

                      <span
                        className={`clause-status ${clauseClass}`}
                      >
                        {clauseStatus}
                      </span>

                    </div>


                    <p>
                      {clause.description ||
                        clause.text ||
                        "Clause detected by the Legal-BERT classifier."}
                    </p>


                    {clause.confidence !== undefined && (

                      <div className="confidence">

                        <span>
                          Confidence
                        </span>

                        <strong>
                          {formatConfidence(
                            clause.confidence
                          )}
                        </strong>

                      </div>

                    )}

                  </div>

                );
              })

            )}

          </div>

        </section>


        {/* =================================================
            ANALYSIS METADATA
        ================================================= */}

        <section className="dashboard-card">

          <div className="section-heading">

            <div>

              <span className="card-label">
                ANALYSIS DETAILS
              </span>

              <h3>
                Processing Information
              </h3>

            </div>

          </div>


          <div className="entity-list">

            <div className="entity-row">

              <span>
                File type
              </span>

              <strong>
                {analysisResults.metadata?.file_type ||
                  "—"}
              </strong>

            </div>


            <div className="entity-row">

              <span>
                Text characters
              </span>

              <strong>
                {analysisResults.metadata?.text_characters ??
                  "—"}
              </strong>

            </div>


            <div className="entity-row">

              <span>
                Segments analyzed
              </span>

              <strong>
                {analysisResults.metadata?.segments_analyzed ??
                  "—"}
              </strong>

            </div>


            <div className="entity-row">

              <span>
                Model classes
              </span>

              <strong>
                {analysisResults.metadata?.model_classes ??
                  "41"}
              </strong>

            </div>


            <div className="entity-row">

              <span>
                OCR used
              </span>

              <strong>
                {analysisResults.metadata?.ocr_used
                  ? "Yes"
                  : "No"}
              </strong>

            </div>


            <div className="entity-row">

              <span>
                Minimum confidence
              </span>

              <strong>
                {analysisResults.metadata
                  ?.minimum_clause_confidence !==
                undefined
                  ? formatConfidence(
                      analysisResults.metadata
                        .minimum_clause_confidence
                    )
                  : "—"}
              </strong>

            </div>

          </div>

        </section>


        {/* =================================================
            DISCLAIMER
        ================================================= */}

        <div className="demo-note">

          <strong>
            Analysis notice:
          </strong>{" "}

          {analysisResults.disclaimer ||
            "Risk scores are application-level indicators generated from model predictions and configured risk policies. They are not legal advice."}

        </div>

      </main>
    );
  };


  /*
   * =========================================================
   * MAIN APPLICATION
   * =========================================================
   */

  return (
    <div className="app">

      {/* =====================================================
          NAVIGATION
      ===================================================== */}

      <header className="navbar">

        <div className="brand">

          <div className="brand-icon">
            CI
          </div>

          <div>

            <h1>
              Contract Intelligence
            </h1>

            <p>
              AI-Powered Legal Analysis
            </p>

          </div>

        </div>


        <div className="system-status">

          <span className="status-dot"></span>

          AI Analysis Ready

        </div>

      </header>


      {/* =====================================================
          SCREENS
      ===================================================== */}

      {screen === "upload" &&
        renderUploadScreen()}

      {screen === "processing" &&
        renderProcessingScreen()}

      {screen === "results" &&
        renderResultsScreen()}

    </div>
  );
}

export default App;