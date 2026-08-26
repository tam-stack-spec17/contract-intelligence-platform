import { useState } from "react";
import { uploadContract } from "./services/api";
import mockResults from "./services/mockData";

function App() {
  const [file, setFile] = useState(null);
  const [screen, setScreen] = useState("upload");
  const [analysisResults, setAnalysisResults] = useState(mockResults);
  const [error, setError] = useState("");

  /*
   * FILE SELECTION + VALIDATION
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
      alert("Please upload a PDF or DOCX file.");

      event.target.value = "";

      setFile(null);

      return;
    }

    setError("");
    setFile(selectedFile);
  };

  /*
   * CONTRACT ANALYSIS
   *
   * First attempts to communicate with FastAPI.
   *
   * If FastAPI is unavailable, the application
   * falls back to mockData.js so the dashboard
   * can still be demonstrated.
   */

  const analyzeContract = async () => {
    if (!file) {
      alert("Please select a contract first.");
      return;
    }

    setError("");
    setScreen("processing");

    try {
      const result = await uploadContract(file);

      console.log("Backend analysis result:", result);

      setAnalysisResults(result);

      setTimeout(() => {
        setScreen("results");
      }, 800);
    } catch (error) {
      console.warn(
        "FastAPI is not available yet. Using demo results.",
        error
      );

      setAnalysisResults({
        ...mockResults,
        contract_name: file.name,
      });

      setTimeout(() => {
        setScreen("results");
      }, 1500);
    }
  };

  /*
   * RESET
   */

  const resetAnalysis = () => {
    setFile(null);
    setError("");
    setAnalysisResults(mockResults);
    setScreen("upload");
  };

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

          System Ready

        </div>

      </header>


      {/* =====================================================
          UPLOAD SCREEN
      ===================================================== */}

      {screen === "upload" && (

        <main className="main-content">

          <section className="hero">

            {/* HERO TEXT */}

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


            {/* UPLOAD CARD */}

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


              {/* FILE INPUT */}

              <label className="upload-button">

                Choose Contract

                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={handleFileChange}
                />

              </label>


              {/* ERROR */}

              {error && (

                <div className="upload-error">
                  {error}
                </div>

              )}


              {/* SELECTED FILE */}

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


          {/* =====================================================
              FEATURES
          ===================================================== */}

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

              {/* FEATURE 1 */}

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


              {/* FEATURE 2 */}

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


              {/* FEATURE 3 */}

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

      )}


      {/* =====================================================
          PROCESSING SCREEN
      ===================================================== */}

      {screen === "processing" && (

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
              factors.
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
                • NLP analysis in progress
              </span>

            </div>

          </div>

        </main>

      )}


      {/* =====================================================
          RESULTS DASHBOARD
      ===================================================== */}

      {screen === "results" && (

        <main className="dashboard">

          {/* DASHBOARD HEADER */}

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

            {/* RISK SCORE */}

            <div className="risk-card">

              <div>

                <span className="card-label">
                  OVERALL CONTRACT RISK
                </span>

                <div className="risk-score">

                  {analysisResults.risk_score}

                  <span>
                    /100
                  </span>

                </div>

                <span className="high-risk-label">
                  {analysisResults.risk_level}
                </span>

              </div>


              <div className="risk-gauge">

                <div className="gauge-inner">

                  <strong>
                    {analysisResults.risk_score}
                  </strong>

                  <span>
                    Risk Score
                  </span>

                </div>

              </div>

            </div>


            {/* ENTITIES */}

            <div className="summary-card">

              <span className="card-label">
                ENTITIES
              </span>

              <strong>
                {analysisResults.entities?.length || 0}
              </strong>

              <p>
                Key entities identified
              </p>

            </div>


            {/* CLAUSES */}

            <div className="summary-card">

              <span className="card-label">
                CLAUSES
              </span>

              <strong>
                {analysisResults.clauses?.length || 0}
              </strong>

              <p>
                Legal clauses detected
              </p>

            </div>


            {/* FINDINGS */}

            <div className="summary-card">

              <span className="card-label">
                RISK FINDINGS
              </span>

              <strong>
                {analysisResults.findings?.length || 0}
              </strong>

              <p>
                Items requiring review
              </p>

            </div>

          </section>


          {/* =================================================
              ENTITIES + RISK FINDINGS
          ================================================= */}

          <section className="dashboard-grid">

            {/* EXTRACTED ENTITIES */}

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

                  {analysisResults.entities?.length || 0}

                </span>

              </div>


              <div className="entity-list">

                {analysisResults.entities?.map(
                  (entity, index) => (

                    <div
                      className="entity-row"
                      key={`${entity.label}-${index}`}
                    >

                      <span>
                        {entity.label}
                      </span>

                      <strong>
                        {entity.value}
                      </strong>

                    </div>

                  )
                )}

              </div>

            </div>


            {/* RISK FINDINGS */}

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

                  {analysisResults.findings?.length || 0}

                </span>

              </div>


              <div className="finding-list">

                {analysisResults.findings?.map(
                  (finding, index) => (

                    <div
                      className="finding"
                      key={`${finding.title}-${index}`}
                    >

                      <span
                        className={`risk-badge ${finding.level}`}
                      >
                        {finding.level}
                      </span>

                      <div>

                        <strong>
                          {finding.title}
                        </strong>

                        <p>
                          {finding.description ||
                            finding.text}
                        </p>

                      </div>

                    </div>

                  )
                )}

              </div>

            </div>

          </section>


          {/* =================================================
              DETECTED CLAUSES
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

                {analysisResults.clauses?.length || 0}

              </span>

            </div>


            <div className="clause-grid">

              {analysisResults.clauses?.map(
                (clause, index) => (

                  <div
                    className="clause-card"
                    key={`${clause.name}-${index}`}
                  >

                    <div className="clause-top">

                      <h4>
                        {clause.name}
                      </h4>

                      <span
                        className={`clause-status ${
                          clause.status?.includes("High")
                            ? "high"
                            : clause.status?.includes("Medium")
                            ? "medium"
                            : "normal"
                        }`}
                      >
                        {clause.status}
                      </span>

                    </div>

                    <p>
                      {clause.description}
                    </p>


                    {/* CONFIDENCE */}

                    {clause.confidence !== undefined && (

                      <div className="confidence">

                        <span>
                          Confidence
                        </span>

                        <strong>
                          {Math.round(
                            clause.confidence * 100
                          )}
                          %
                        </strong>

                      </div>

                    )}

                  </div>

                )
              )}

            </div>

          </section>


          {/* =================================================
              DEMO INFORMATION
          ================================================= */}

          <div className="demo-note">

            <strong>
              Demo mode:
            </strong>{" "}

            The dashboard uses mock results when
            the FastAPI backend is unavailable.
            Once the backend is connected, real
            ML/NLP predictions will be displayed here.

          </div>

        </main>

      )}

    </div>
  );
}

export default App;