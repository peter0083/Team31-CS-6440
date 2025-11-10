// MS4TrialMatchResults.jsx - Enhanced to show trial name and location

import React, { useState, useEffect } from "react";

const MS4TrialMatchResults = ({ trialData, patients = [] }) => {
  const [matchResults, setMatchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedPatient, setExpandedPatient] = useState(null);
  const [sortBy, setSortBy] = useState("score");

  const API_MS4_URL = import.meta.env.VITE_API_MS4_URL || "http://localhost:8004";

  // Extract trial info
  const trialId = trialData?.nct_id || "";
  const trialTitle = trialData?.official_title || trialData?.title || "Unknown Trial";
  const trialLocation = trialData?.location || trialData?.locations?.[0] || "Location not available";
  const trialPhase = trialData?.phase || "Unknown";

  useEffect(() => {
    console.log("🔍 MS4TrialMatchResults mounted with:", {
      trialId,
      trialTitle,
      patients: patients.length,
    });

    if (trialId && patients.length > 0) {
      fetchMatchResults();
    }
  }, [trialId, patients]);

  const fetchMatchResults = async () => {
  try {
    // Build the trial object
    const trialObject = {
      nct_id: trialId,
      official_title: trialTitle,
      // Add other trial fields as needed
    };

    const patientIds = patients.map(p => p.patient_id || p.id);

    console.log("📤 Sending match request:", { trialId, patientIds });

    const response = await fetch(`${API_MS4_URL}/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        raw_patients: JSON.stringify(patients),
        raw_trial: JSON.stringify(trialObject)
      })
    });


      console.log("📥 Response status:", response.status);

      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }

      const data = await response.json();
      console.log("📊 Match results:", data);

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
      <div style={{ padding: "20px", textAlign: "center", color: "#666" }}>
        ⏳ Analyzing patient-trial compatibility...
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        style={{
          padding: "20px",
          backgroundColor: "#f8d7da",
          color: "#721c24",
          borderRadius: "4px",
          marginTop: "20px",
        }}
      >
        ❌ {error}
      </div>
    );
  }

  // No patients state
  if (!patients.length) {
    return (
      <div
        style={{
          padding: "20px",
          backgroundColor: "#e2e3e5",
          color: "#383d41",
          borderRadius: "4px",
          marginTop: "20px",
        }}
      >
        No patient data available for matching.
      </div>
    );
  }

  // No results state
  if (matchResults.length === 0) {
    return (
      <div
        style={{
          padding: "20px",
          backgroundColor: "#fff3cd",
          color: "#856404",
          borderRadius: "4px",
          marginTop: "20px",
        }}
      >
        ⚠️ No match results available yet.
      </div>
    );
  }

  const matchLabel =
    matchResults.length === 1
      ? "1 patient matches"
      : `${matchResults.length} patients match`;

  return (
    <div style={{ marginTop: "30px", borderTop: "2px solid #ddd", paddingTop: "20px" }}>
      {/* Trial Header with Name and Location */}
      <div
        style={{
          backgroundColor: "#f8f9fa",
          padding: "20px",
          borderRadius: "8px",
          marginBottom: "20px",
          border: "1px solid #dee2e6",
        }}
      >
        <div style={{ marginBottom: "15px" }}>
          <div style={{ fontSize: "11px", color: "#666", textTransform: "uppercase" }}>
            Trial ID: {trialId}
          </div>
          <h3
            style={{
              margin: "8px 0",
              fontSize: "18px",
              fontWeight: "600",
              color: "#333",
            }}
          >
            {trialTitle}
          </h3>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "15px",
            fontSize: "14px",
          }}
        >
          <div>
            <strong>Location:</strong>
            <div style={{ color: "#666", marginTop: "4px" }}>{trialLocation}</div>
          </div>
          <div>
            <strong>Phase:</strong>
            <div style={{ color: "#666", marginTop: "4px" }}>{trialPhase}</div>
          </div>
          <div>
            <strong>Patient Matches:</strong>
            <div
              style={{
                color: "#28a745",
                fontWeight: "600",
                marginTop: "4px",
                fontSize: "18px",
              }}
            >
              {matchResults.length}
            </div>
          </div>
        </div>
      </div>

      {/* Results Summary */}
      <div
        style={{
          padding: "15px",
          backgroundColor: "#d4edda",
          color: "#155724",
          borderRadius: "4px",
          marginBottom: "20px",
          textAlign: "center",
          fontWeight: "500",
        }}
      >
        ✅ Found <strong>{matchResults.length}</strong> {matchLabel} for trial{" "}
        <strong>{trialId}</strong>
      </div>

      {/* Sort Controls */}
      <div style={{ marginBottom: "20px", display: "flex", gap: "10px" }}>
        <label style={{ fontSize: "14px", fontWeight: "500" }}>Sort by:</label>
        <select
          value={sortBy}
          onChange={(e) => {
            setSortBy(e.target.value);
            setMatchResults(sortResults(matchResults));
          }}
          style={{
            padding: "6px 10px",
            border: "1px solid #ddd",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          <option value="score">Compatibility Score</option>
          <option value="percentage">Match Percentage</option>
          <option value="name">Patient ID</option>
        </select>
      </div>

      {/* Patient Results List */}
      <div>
        {matchResults.map((result) => {
          const isExpanded = expandedPatient === result.patient_id;
          const percentage = (result.percentage || 0).toFixed(0);
          const qualityClass = getMatchQualityClass(percentage);
          const qualityLabel = getMatchQualityLabel(percentage);

          return (
            <div
              key={result.patient_id}
              style={{
                border: "1px solid #ddd",
                borderRadius: "6px",
                padding: "15px",
                marginBottom: "10px",
                backgroundColor: isExpanded ? "#f8f9fa" : "#fff",
                cursor: "pointer",
                transition: "background-color 0.2s",
              }}
              onClick={() => togglePatientExpanded(result.patient_id)}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "auto 1fr auto",
                  alignItems: "center",
                  gap: "15px",
                }}
              >
                {/* Match Quality Badge */}
                <div
                  style={{
                    width: "60px",
                    height: "60px",
                    borderRadius: "50%",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: "bold",
                    color: "#fff",
                    backgroundColor:
                      qualityClass === "match-excellent"
                        ? "#28a745"
                        : qualityClass === "match-good"
                        ? "#17a2b8"
                        : qualityClass === "match-fair"
                        ? "#ffc107"
                        : "#dc3545",
                  }}
                >
                  <div style={{ fontSize: "20px" }}>{percentage}%</div>
                  <div style={{ fontSize: "10px" }}>Match</div>
                </div>

                {/* Patient Info */}
                <div>
                  <div style={{ fontWeight: "600", fontSize: "16px", marginBottom: "4px" }}>
                    Patient {result.patient_id}
                  </div>
                  <div style={{ fontSize: "13px", color: "#666" }}>
                    {qualityLabel} • Score: {(result.score || 0).toFixed(2)}
                  </div>
                </div>

                {/* Expand Button */}
                <div style={{ fontSize: "20px" }}>
                  {isExpanded ? "▼" : "▶"}
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div style={{ marginTop: "15px", paddingTop: "15px", borderTop: "1px solid #dee2e6" }}>
                  <div style={{ fontSize: "14px", color: "#333" }}>
                    <strong>Eligibility Criteria Met:</strong>
                    <div style={{ color: "#666", marginTop: "8px" }}>
                      Patient meets <strong>{percentage}%</strong> of the trial's eligibility
                      criteria with a compatibility score of <strong>{(result.score || 0).toFixed(2)}</strong>.
                    </div>
                  </div>

                  {/* Criteria Details */}
                  {result.criteria && result.criteria.length > 0 && (
                    <div style={{ marginTop: "12px" }}>
                      <strong>Matching Criteria:</strong>
                      <div style={{ marginTop: "8px" }}>
                        {result.criteria.map((criterion, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: "8px",
                              backgroundColor: "#f0f0f0",
                              borderRadius: "3px",
                              marginBottom: "6px",
                              fontSize: "13px",
                              fontFamily: "monospace",
                            }}
                          >
                            ✓ {criterion.rawText || criterion.text}
                          </div>
                        ))}
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
