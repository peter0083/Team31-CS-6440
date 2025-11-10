import React, { useState, useEffect } from "react";

/**
 * MS4TrialMatchResults Component
 * Displays patients matched to clinical trials with their compatibility scores
 *
 * Shows:
 * - Trial information (title, criteria count)
 * - Matched patients ranked by compatibility
 * - Patient demographics and match details
 * - Visual score indicators
 */

const MS4TrialMatchResults = ({ trialId, patients = [] }) => {
  const [matchResults, setMatchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedPatient, setExpandedPatient] = useState(null);
  const [sortBy, setSortBy] = useState("score");

  const API_MS4_URL =
    import.meta.env.VITE_API_MS4_URL || "http://localhost:8004";

  useEffect(() => {
    console.log("🔍 MS4TrialMatchResults mounted with:", { trialId, patients: patients.length });
    if (trialId && patients.length > 0) {
      fetchMatchResults();
    }
  }, [trialId, patients]);

  const fetchMatchResults = async () => {
    setLoading(true);
    setError("");
    try {
      const patientIds = patients.map((p) => p.id || p.patient_id);
      console.log("📤 Sending match request:", { trialId, patientIds });

      const response = await fetch(`${API_MS4_URL}/api/ms4/match-trial`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nct_id: trialId, patient_ids: patientIds }),
      });

      console.log("📥 Response status:", response.status);

      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }

      const data = await response.json();
      console.log("📊 Match results:", data);

      // Handle different response formats
      const results = data.results || data.matches || data.data || [];
      console.log("✅ Parsed results:", results);

      const sorted = sortResults(results);
      setMatchResults(sorted);
    } catch (err) {
      console.error("❌ Error fetching match results:", err);
      setError(`Failed to load match results: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const sortResults = (results) => {
    const sorted = [...results];
    switch (sortBy) {
      case "percentage":
        return sorted.sort((a, b) => (b.percentage || 0) - (a.percentage || 0));
      case "name":
        return sorted.sort((a, b) =>
          (a.patient_id || "").localeCompare(b.patient_id || "")
        );
      case "score":
      default:
        return sorted.sort((a, b) => (b.score || 0) - (a.score || 0));
    }
  };

  const togglePatientExpanded = (patientId) => {
    setExpandedPatient(expandedPatient === patientId ? null : patientId);
  };

  const getMatchQualityClass = (percentage) => {
    if (percentage >= 80) return "match-excellent";
    if (percentage >= 60) return "match-good";
    if (percentage >= 40) return "match-fair";
    return "match-poor";
  };

  const getMatchQualityLabel = (percentage) => {
    if (percentage >= 80) return "Excellent Match";
    if (percentage >= 60) return "Good Match";
    if (percentage >= 40) return "Fair Match";
    return "Poor Match";
  };

  // Loading state
  if (loading) {
    return (
      <div className="match-results-loading">
        <div className="spinner"></div>
        <p>⏳ Analyzing patient-trial compatibility...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="alert alert-error">
        <p>❌ {error}</p>
        <details>
          <summary>Debug Info</summary>
          <pre>
            trialId: {trialId}
            {"\n"}
            patients: {patients.length}
            {"\n"}
            API_MS4_URL: {API_MS4_URL}
          </pre>
        </details>
      </div>
    );
  }

  // No patients
  if (!patients || patients.length === 0) {
    return (
      <div className="match-results-empty">
        <p>No patient data available for matching.</p>
      </div>
    );
  }

  // No results from API
  if (matchResults.length === 0) {
    return (
      <div className="match-results-empty">
        <p>⚠️ No match results available yet.</p>
        <p style={{ fontSize: "0.9rem", opacity: 0.7 }}>
          Trial ID: {trialId}
          <br />
          Patients: {patients.length}
        </p>
        <button onClick={fetchMatchResults} className="btn btn--secondary">
          🔄 Retry
        </button>
      </div>
    );
  }

  // Display results
  return (
    <div className="match-results-container">
      {/* Sort Controls */}
      <div className="match-controls">
        <label htmlFor="sort-by">Sort by:</label>
        <select
          id="sort-by"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="form-control"
        >
          <option value="score">Compatibility Score</option>
          <option value="percentage">Percentage Match</option>
          <option value="name">Patient ID</option>
        </select>
      </div>

      {/* Results Summary */}
      <div className="results-summary">
        <p>
          Found <strong>{matchResults.length}</strong> patients analyzed for
          trial <strong>{trialId}</strong>
        </p>
      </div>

      {/* Patient Results */}
      <div className="match-results-list">
        {matchResults.map((result) => {
          const isExpanded = expandedPatient === result.patient_id;
          const matchQuality = getMatchQualityClass(result.percentage || 0);
          const matchLabel = getMatchQualityLabel(result.percentage || 0);

          return (
            <div key={result.patient_id} className="patient-match-card card">
              {/* Card Header */}
              <div
                className={`match-card-header ${matchQuality}`}
                onClick={() => togglePatientExpanded(result.patient_id)}
              >
                <div className="patient-info">
                  <h3 className="patient-name">Patient {result.patient_id}</h3>
                  <p className="match-status">{matchLabel}</p>
                </div>

                <div className="match-score-badge">
                  <div className="score-value">
                    {(result.percentage || 0).toFixed(0)}%
                  </div>
                  <div className="score-label">Match</div>
                </div>

                <span className="toggle-icon">
                  {isExpanded ? "▼" : "▶"}
                </span>
              </div>

              {/* Card Body (Expanded) */}
              {isExpanded && (
                <div className="match-card-body">
                  {/* Overall Assessment */}
                  <div className="assessment-section">
                    <h4>Overall Assessment</h4>
                    <p>
                      Patient meets <strong>{(result.percentage || 0).toFixed(0)}%</strong> of the
                      trial's eligibility criteria with a compatibility score of{" "}
                      <strong>{(result.score || 0).toFixed(2)}</strong>.
                    </p>
                  </div>

                  {/* Criteria Rules */}
                  {result.criteria && result.criteria.length > 0 && (
                    <div className="criteria-section">
                      <h4>Eligibility Criteria</h4>
                      <ul className="criteria-list">
                        {result.criteria.map((criterion, idx) => (
                          <li key={idx} className="criterion-item">
                            <strong>Rule {criterion.ruleId}:</strong>{" "}
                            {criterion.description}
                            {criterion.rawText && (
                              <div className="criterion-raw">
                                <code>{criterion.rawText}</code>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Demographics */}
                  {result.demographics && (
                    <div className="demographics-section">
                      <h4>Patient Demographics</h4>
                      <div className="demographics-grid">
                        {Object.entries(result.demographics).map(
                          ([key, value]) => (
                            <div key={key} className="demographic-item">
                              <span className="label">
                                {key.replace(/_/g, " ")}:
                              </span>
                              <span className="value">{value}</span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MS4TrialMatchResults;
