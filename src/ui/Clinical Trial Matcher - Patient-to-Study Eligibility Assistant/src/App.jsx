import React, { useState, useEffect } from "react";
import MS2HealthStatus from "./components/MS2HealthStatus.jsx";
import MS3HealthStatus from "./components/MS3HealthStatus.jsx";

function App() {
  const [selectedCondition, setSelectedCondition] = useState("diabetes");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [parsedCache, setParsedCache] = useState({});
  const [expandedTrial, setExpandedTrial] = useState(null);

  const CONDITIONS = ["diabetes", "dementia", "cancer"];

  const API_SEARCH_URL =
    import.meta.env.VITE_API_SEARCH_URL || "http://localhost:8001/search-trials";
  const API_MS2_URL =
    import.meta.env.VITE_API_DISPLAY_URL || "http://localhost:8002/api/ms2";

  const handleSearch = async () => {
    setError("");
    setResults(null);
    setLoading(true);
    try {
      const res = await fetch(API_SEARCH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term: selectedCondition }),
      });
      const data = await res.json();
      if (data.trials && data.trials.length > 0) {
        setResults(data);
        setError("");
        fetchParsedCriteria(data.trials);
      } else if (data.message) {
        setError(data.message);
        setResults(null);
      } else {
        setError("❌ No trials found");
        setResults(null);
      }
    } catch (error) {
      console.error("API Error:", error);
      setError("❌ Error fetching data. Please try again.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchParsedCriteria = async (trials) => {
    const cache = { ...parsedCache };
    for (const trial of trials) {
      const nctId = trial.nct_id;
      if (cache[nctId]) continue;
      try {
        const response = await fetch(`${API_MS2_URL}/parsed-criteria/${nctId}`);
        if (response.ok) {
          const parsed = await response.json();
          cache[nctId] = parsed;
        }
      } catch (err) {
        console.error(`Error fetching criteria for ${nctId}:`, err);
      }
    }
    setParsedCache(cache);
  };

  const toggleExpanded = (nctId) => {
    setExpandedTrial(expandedTrial === nctId ? null : nctId);
  };

  return (
    <div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto" }}>
      <h1>🏥 Clinical Trial Finder</h1>
      <p>Select a condition and discover clinical trials that match your health needs</p>

      {/* Health Status Components */}
      <div style={{ backgroundColor: "#f8f9fa", padding: "15px", borderRadius: "8px", marginBottom: "20px" }}>
        <h3 style={{ margin: "0 0 10px 0", fontSize: "14px", color: "#333" }}>🔍 Service Status</h3>
        <MS2HealthStatus />
        <MS3HealthStatus />
      </div>

      {/* Condition Selection */}
      <div style={{ marginBottom: "20px" }}>
        <label htmlFor="condition-select" style={{ fontWeight: "bold", marginRight: "10px" }}>
          Select Condition:
        </label>
        <select
          id="condition-select"
          value={selectedCondition}
          onChange={(e) => setSelectedCondition(e.target.value)}
          style={{
            padding: "8px 12px",
            borderRadius: "4px",
            border: "1px solid #ddd",
            fontSize: "14px",
          }}
        >
          {CONDITIONS.map((cond) => (
            <option key={cond} value={cond}>
              {cond.charAt(0).toUpperCase() + cond.slice(1)}
            </option>
          ))}
        </select>
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            marginLeft: "10px",
            padding: "8px 20px",
            backgroundColor: loading ? "#ccc" : "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: "bold",
          }}
        >
          {loading ? "Fetching studies..." : "Search"}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div style={{ color: "#dc3545", padding: "10px", backgroundColor: "#f8d7da", borderRadius: "4px", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {/* Results */}
      {results && results.trials && results.trials.length > 0 ? (
        <div style={{ backgroundColor: "#f9f9f9", padding: "20px", borderRadius: "8px" }}>
          <h2>Found {results.trials.length} Clinical Trials</h2>
          {results.trials.map((trial) => {
            const parsed = parsedCache[trial.nct_id];
            const isExpanded = expandedTrial === trial.nct_id;

            return (
              <div
                key={trial.nct_id}
                style={{
                  border: "1px solid #ddd",
                  padding: "15px",
                  marginBottom: "15px",
                  borderRadius: "6px",
                  backgroundColor: "white",
                  cursor: "pointer",
                  transition: "box-shadow 0.3s",
                }}
                onClick={() => toggleExpanded(trial.nct_id)}
              >
                <h3 style={{ margin: "0 0 10px 0", color: "#007bff" }}>
                  {trial.nct_id}: {trial.title}
                </h3>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginBottom: "10px" }}>
                  <div>
                    <strong>Status:</strong> {trial.recruitment_status || "N/A"}
                  </div>
                  <div>
                    <strong>Location:</strong> {trial.location || "N/A"}
                  </div>
                  <div>
                    <strong>Phase:</strong> {trial.phase?.join(", ") || "Not specified"}
                  </div>
                  <div>
                    <strong>Sponsor:</strong> {trial.sponsor || "N/A"}
                  </div>
                </div>

                {isExpanded && (
                  <div style={{ marginTop: "15px", paddingTop: "15px", borderTop: "1px solid #eee" }}>
                    <div style={{ marginBottom: "15px" }}>
                      <strong>Description:</strong>
                      <p style={{ fontSize: "14px", color: "#555" }}>{trial.brief_summary}</p>
                    </div>

                    {parsed && (
                      <div style={{ backgroundColor: "#f0f0f0", padding: "10px", borderRadius: "4px", marginBottom: "15px" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                          <div>
                            <strong>Model Used:</strong>
                            <p>{parsed.model_used}</p>
                          </div>
                          <div>
                            <strong>Confidence:</strong>
                            <p>{(parsed.parsing_confidence * 100).toFixed(0)}%</p>
                          </div>
                          <div>
                            <strong>Rules Extracted:</strong>
                            <p>{parsed.total_rules_extracted}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
                      <div>
                        <strong>✅ Inclusion Criteria:</strong>
                        <ul style={{ fontSize: "13px", marginTop: "5px" }}>
                          {(parsed?.inclusion_criteria || []).slice(0, 3).map((criterion, idx) => (
                            <li key={idx}>{criterion.rule}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <strong>❌ Exclusion Criteria:</strong>
                        <ul style={{ fontSize: "13px", marginTop: "5px" }}>
                          {(parsed?.exclusion_criteria || []).slice(0, 3).map((criterion, idx) => (
                            <li key={idx}>{criterion.rule}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <p style={{ fontSize: "12px", color: "#999", marginTop: "10px" }}>
                      Click to collapse
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : !loading && results === null ? (
        <div style={{ padding: "40px", textAlign: "center", backgroundColor: "#f9f9f9", borderRadius: "8px" }}>
          <p>Select a condition above and click Search to find trials.</p>
        </div>
      ) : !loading && results && results.trials?.length === 0 ? (
        <div style={{ padding: "40px", textAlign: "center", backgroundColor: "#f9f9f9", borderRadius: "8px" }}>
          <p>No trials found. Try another condition.</p>
        </div>
      ) : null}
    </div>
  );
}

export default App;
