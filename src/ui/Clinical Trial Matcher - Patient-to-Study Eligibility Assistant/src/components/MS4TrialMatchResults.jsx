// MS4TrialMatchResults.jsx - Enhanced to show trial name and location

import React, { useState, useEffect } from "react";

const MS4TrialMatchResults = ({ trialData, patients = [] }) => {
  const [matchResults, setMatchResults] = useState([]);
  const [exclusion_count, setExclusionCount] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedPatient, setExpandedPatient] = useState(null);
  const [expandedExcluded, setExpandedExcluded] = useState(null);
  const [sortBy, setSortBy] = useState("score");

  const API_MS4_URL = import.meta.env.VITE_API_MS4_URL || "http://localhost:8004";

  // Extract trial info
  const trialId = typeof trialData === 'string'
    ? trialData
    : (trialData?.nct_id || trialData?.nctid || trialData?.NCT_ID);
  const trialTitle = typeof trialData === 'object'
    ? (trialData?.official_title || trialData?.title || 'Unknown Trial')
    : 'Unknown Trial';
  const trialLocation = trialData?.location || trialData?.locations?.[0] || "Location not available";
  const trialPhase = trialData?.phase || "Unknown";

  useEffect(() => {
    console.log("🔍 MS4TrialMatchResults mounted with:", {
      trialId,
      trialTitle,
      patients: patients.length,
    });

      if (trialId) {
          fetchMatchResults();
      }
  }, [trialId]);


  const fetchMatchResults = async () => {
    try {
        const payload = {
          nct_id: trialId,
          limit: 10,
        };

        // pay load debug
        console.log("🚀 Full Payload Object:", payload);
        console.log("🚀 Payload as JSON:", JSON.stringify(payload));
        console.log("🚀 trialId value:", trialId, "type:", typeof trialId);

    const response = await fetch(`${API_MS4_URL}/match-trial`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

      console.log("📥 Response status:", response.status);

      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }

      const data = await response.json();
      console.log("📊 Match results:", data);

      const results = data.ranked_results || [];
      console.log("✅ Parsed results:", results);

      setExclusionCount(data.exclusion_count || 0);
      console.log("✅ Parsed exclusion_count:", exclusion_count);

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
  // ✅ Add safety check
  if (!Array.isArray(results)) {
    console.warn("sortResults received non-array:", results);
    return [];
  }

  const sorted = [...results];
  if (!Array.isArray(results)) {
      console.warn("sortResults received non-array:", results);
      return [];
    }

  switch (sortBy) {
    case "percentage":
      return sorted.sort(
        (a, b) => (b.match_percentage || 0) - (a.match_percentage || 0)
      );
    case "name":
      return sorted.sort((a, b) =>
        (a.patient_id || "").localeCompare(b.patient_id || "")
      );
    case "rank":
    default:
      return sorted.sort((a, b) => (a.rank || 999) - (b.rank || 999));
    }
  };

  const togglePatientExpanded = (patientId) => {
    setExpandedPatient(expandedPatient === patientId ? null : patientId);
  };

 const toggleExpandedExclude = (patientId) => {
    setExpandedExcluded(expandedExcluded === patientId ? null : patientId);
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
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '15px',
              fontSize: '14px',
              backgroundColor: '#1a1a1a',
              padding: '16px',
              borderRadius: '8px'
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

      {/* Match Results Summary */}
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
        ✅ Displaying the top <strong>{matchResults.length}</strong> patient{matchResults.length !== 1 ? 's' : ''} match for trial <strong>{trialId}</strong>
      </div>

      {/* Patient Results List */}
            <div>
        {matchResults.map((result) => {
          const isExpanded = expandedPatient === result.patient_id;
          const percentage = (result.match_percentage || 0).toFixed(0);
          const qualityClass = getMatchQualityClass(percentage);
          const qualityLabel = getMatchQualityLabel(percentage);
          const isInclusion = result.isInclusion
          const matches = result.matches
          const types = result.types
          const fields = result.fields
          const operators = result.operators
          const values = result.values
          const patient_values = result.patient_values

          return (
            <div
              key={result.patientid}
              style={{
                border: '1px solid #ddd',
                borderRadius: '6px',
                padding: '15px',
                marginBottom: '10px',
                backgroundColor: isExpanded ? '#f8f9fa' : '#fff',
                cursor: 'pointer',
                transition: 'background-color 0.2s',
              }}
              onClick={() => togglePatientExpanded(result.patient_id)}
            >
              {/* Collapsed View */}
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr auto', alignItems: 'center', gap: '15px' }}>
                {/* Match Quality Badge */}
                <div
                  style={{
                    width: '60px',
                    height: '60px',
                    borderRadius: '50%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 'bold',
                    color: '#fff',
                    backgroundColor:
                      qualityClass === 'match-excellent' ? '#28a745' :
                      qualityClass === 'match-good' ? '#17a2b8' :
                      qualityClass === 'match-fair' ? '#ffc107' : '#dc3545',
                  }}
                >
                  <div style={{ fontSize: '20px' }}>{percentage}</div>
                  <div style={{ fontSize: '10px' }}>Match</div>
                </div>

                {/* Patient Info */}
                <div>
                  <div style={{ fontWeight: '600', fontSize: '16px', marginBottom: '4px', color: '#333' }}>
                    Patient {result.patient_id}
                  </div>
                  <div style={{ fontSize: '13px', color: '#666' }}>
                    {qualityLabel} - Score: {(result.match_percentage || 0).toFixed(2)}
                  </div>
                </div>

                {/* Expand Arrow */}
                <div style={{ fontSize: '18px', color: '#666' }}>
                  {isExpanded ? '▼' : '▶'}
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px solid #dee2e6' }}>
                  <div style={{ color: '#666', marginTop: '8px' }}>
                    Patient meets <strong>{percentage}</strong>% of the trial's eligibility criteria.
                  </div>
                  <div style={{ color: '#666', marginTop: '8px' }}>
                    <strong>Inclusion Criteria</strong>
                  </div>
                     <table
                        style={{
                            borderCollapse: "collapse",
                            border: "1px solid black",
                        }}
                     >
                          <thead>
                            <tr>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Matches</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Type</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Field</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Patient Value</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Operator</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Requirement</th>
                            </tr>
                          </thead>
                          <tbody>
                                {matches.map((match, i) =>
                                    isInclusion[i] ? (
                                      <tr key={i}>
                                        <td style={{ border: "1px solid black", padding: "4px" }}>
                                          {match ? "✅" : "❌"}
                                        </td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{types[i]}</td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{fields[i]}</td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{patient_values[i]}</td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{operators[i]}</td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{values[i]}</td>
                                      </tr>
                                    ) : null
                                  )}
                          </tbody>
                     </table>
                    <div style={{ color: '#666', marginTop: '8px' }}>
                    <strong>Exclusion Criteria</strong>
                  </div>
                     <table
                        style={{
                            borderCollapse: "collapse",
                            border: "1px solid black",
                        }}
                     >
                          <thead>
                            <tr>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Matches</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Type</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Field</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Patient Value</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Operator</th>
                              <th style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>Requirement</th>
                            </tr>
                          </thead>
                          <tbody>
                                {matches.map((match, i) =>
                                    isInclusion[i]==false ? (
                                      <tr key={i}>
                                        <td style={{ border: "1px solid black", padding: "4px" }}>
                                          {match ? "✅" : "❌"}
                                        </td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{types[i]}</td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{fields[i]}</td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{patient_values[i]}</td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{operators[i]}</td>
                                        <td style={{ border: "1px solid black", padding: "4px" , color: "#333"}}>{values[i]}</td>
                                      </tr>
                                    ) : null
                                  )}
                          </tbody>
                     </table>
                </div>

              )}
            </div>

          );

        })}


            <div>



            </div>
      </div>

    </div>
  );
};

export default MS4TrialMatchResults;
